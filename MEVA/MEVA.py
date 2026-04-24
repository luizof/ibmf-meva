from flask import Flask, jsonify, redirect, render_template, request, url_for
from psycopg2 import sql
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from time import sleep
from collections import defaultdict
import calendar
import concurrent.futures
import logging
import threading
import time

import config
import database
import limits
import queries
from fast_get_distance import fast_get_distance
from get_distance import get_distance
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)

# Horário local (UTC-3) usado para exibir os gráficos
LOCAL_TIME_OFFSET = timedelta(hours=-3)

# Total de leituras por ciclo de medição (3 maiores + 3 menores são descartados
# em superior/inferior antes de calcular a média).
READINGS_PER_CYCLE = 11

# Estado compartilhado entre threads de medição e o Flask.
# - ``measurement_progress``: (machine_id, position_id) -> {'count': int, 'total': int}
#   atualizado em tempo real pela ``measure_sensor_pair``.
# - ``pending_calibrations``: (machine_id, position_id) -> {
#       'block_thickness': Decimal, 'timestamp': datetime,
#       'status': 'waiting'|'done'|'error', 'value': Decimal|None,
#       'error': str|None,
#   }
_state_lock = threading.Lock()
measurement_progress = {}
pending_calibrations = {}


def _set_reading_count(machine_id, position_id, count):
    with _state_lock:
        measurement_progress[(machine_id, position_id)] = {
            'count': count,
            'total': READINGS_PER_CYCLE,
        }


def get_reading_progress(machine_id, position_id):
    with _state_lock:
        return dict(measurement_progress.get((machine_id, position_id), {'count': 0, 'total': READINGS_PER_CYCLE}))


def apply_moving_average(timestamps, values, window_seconds):
    """Return a list of moving averages over a sliding time window.

    ``timestamps`` is a list of ``datetime`` instances; ``values`` is the
    parallel list of numeric (or ``None``) samples. For each ``i``, the returned
    element is the arithmetic mean of every non-None value whose timestamp lies
    in ``[timestamps[i] - window, timestamps[i]]``. ``None`` inputs propagate as
    ``None`` outputs so that gaps in the chart are preserved.
    """
    if not values or window_seconds <= 0:
        return list(values)
    window = timedelta(seconds=window_seconds)
    out = []
    for i, (ts, v) in enumerate(zip(timestamps, values)):
        if v is None or ts is None:
            out.append(None)
            continue
        cutoff = ts - window
        total = 0.0
        count = 0
        # Walk backwards from the current index; stop as soon as we pass the
        # window boundary. Safe for lists with None values interleaved.
        for j in range(i, -1, -1):
            tj = timestamps[j]
            vj = values[j]
            if tj is None:
                continue
            if tj < cutoff:
                break
            if vj is not None:
                total += vj
                count += 1
        out.append(total / count if count else None)
    return out


def _smooth_series(timestamps, values, smoothing):
    """Wrapper that only smooths if ``smoothing.enabled`` is true."""
    if not smoothing or not smoothing.get('enabled'):
        return values
    return apply_moving_average(timestamps, values, smoothing.get('seconds', 30))

def measure_sensor_pair(sensor_pair):
    machine_id = sensor_pair[2]
    position_id = sensor_pair[3]
    logging.info(f"Starting measurement thread for machine {machine_id}, position {position_id}")

    superior_distances = []
    inferior_distances = []
    _set_reading_count(machine_id, position_id, 0)

    loop_start = time.time()

    while True:
        
        superior_ip = sensor_pair[1]
        inferior_ip = sensor_pair[7]

        # Função auxiliar para obter a distância
        def fetch_distance(ip):
            return get_distance(ip, 8899)

        # Use ThreadPoolExecutor para executar as chamadas de forma paralela
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            superior_future = executor.submit(fetch_distance, superior_ip)
            inferior_future = executor.submit(fetch_distance, inferior_ip)

            superior_distance = superior_future.result()
            inferior_distance = inferior_future.result()

        logging.info(
            f"Fetched distances for machine {machine_id}, position {position_id}: "
            f"sup={superior_distance} inf={inferior_distance}"
        )

        logging.info(
            f"Distance fetch for machine {machine_id}, position {position_id} took {time.time() - loop_start:.2f}s"
        )

        # Adicionar as distâncias às listas
        if superior_distance is not None and inferior_distance is not None:
            superior_distances.append(superior_distance)
            inferior_distances.append(inferior_distance)
            _set_reading_count(machine_id, position_id, len(superior_distances))
            logging.info(
                f"Accumulated {len(superior_distances)}/{READINGS_PER_CYCLE} readings for machine {machine_id}, position {position_id}"
            )

        # Se ambas as listas tiverem 5 valores, processe e insira no banco
        if len(superior_distances) == 11 and len(inferior_distances) == 11:
            # Remover valores extremos e calcular a média
            superior_distances.remove(max(superior_distances))
            superior_distances.remove(max(superior_distances))
            superior_distances.remove(max(superior_distances))

            superior_distances.remove(min(superior_distances))
            superior_distances.remove(min(superior_distances))
            superior_distances.remove(min(superior_distances))


            inferior_distances.remove(max(inferior_distances))
            inferior_distances.remove(max(inferior_distances))
            inferior_distances.remove(max(inferior_distances))

            inferior_distances.remove(min(inferior_distances))
            inferior_distances.remove(min(inferior_distances))
            inferior_distances.remove(min(inferior_distances))

            superior_avg = sum(superior_distances) / len(superior_distances)
            inferior_avg = sum(inferior_distances) / len(inferior_distances)

            timestamp = datetime.utcnow()
            data = (timestamp, machine_id, position_id, superior_avg, inferior_avg)
            queries.insert_measurement(data)
            logging.info(
                f"Measurement inserted for machine {machine_id}, position {position_id}: "
                f"sup={superior_avg:.2f} inf={inferior_avg:.2f}"
            )
            logging.info(
                f"Full cycle for machine {machine_id}, position {position_id} took {time.time() - loop_start:.2f}s"
            )
            loop_start = time.time()
            # Limpar as listas para o próximo conjunto de 5 valores
            superior_distances.clear()
            inferior_distances.clear()
            _set_reading_count(machine_id, position_id, 0)

            time.sleep(0.2)

def start_measurement_threads():
    sensor_pairs = queries.get_sensor_pairs()
    logging.info(f"Found {len(sensor_pairs)} sensor pair(s)")
    for pair in sensor_pairs:
        machine_id = pair[2]
        position_id = pair[3]
        logging.info(f"Starting thread for machine {machine_id}, position {position_id}")
        thread = threading.Thread(target=measure_sensor_pair, args=(pair,))
        thread.daemon = True
        thread.start()

# Conexão com o banco de dados
def get_db_conn():
    """Wrapper around :func:`database.connect` for backward compatibility."""
    return database.connect()

def get_maquinas():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Maquinas;")
    maquinas = cur.fetchall()
    cur.close()
    conn.close()
    return maquinas

def get_posicoes():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Posicoes;")
    posicoes = cur.fetchall()
    cur.close()
    conn.close()
    return posicoes

# Página inicial - lista de máquinas
@app.route('/maquinas')
def maquinas():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Maquinas;")
    maquinas = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index_maquinas.html', maquinas=maquinas)

# Adicionar máquina
@app.route('/adicionar_maquina', methods=['GET', 'POST'])
def adicionar_maquina():
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO Maquinas (Nome, Descricao) VALUES (%s, %s);", (nome, descricao))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('maquinas'))
    return render_template('adicionar_maquinas.html')

# Editar máquina
@app.route('/editar_maquina/<int:id>', methods=['GET', 'POST'])
def editar_maquina(id):
    conn = get_db_conn()
    cur = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        descricao = request.form['descricao']
        cur.execute("UPDATE Maquinas SET Nome = %s, Descricao = %s WHERE ID = %s;", (nome, descricao, id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('maquinas'))
    cur.execute("SELECT * FROM Maquinas WHERE ID = %s;", (id,))
    maquina = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('editar_maquinas.html', maquina=maquina)

# Remover máquina
@app.route('/remover_maquina/<int:id>')
def remover_maquina(id):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM Maquinas WHERE ID = %s;", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('maquinas'))

# Página inicial - lista de posições
@app.route('/posicoes')
def posicoes():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Posicoes;")
    posicoes = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index_posicoes.html', posicoes=posicoes)

# Adicionar posição
@app.route('/adicionar_posicao', methods=['GET', 'POST'])
def adicionar_posicao():
    if request.method == 'POST':
        nome_posicao = request.form['nome_posicao']
        descricao_posicao = request.form['descricao_posicao']
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO Posicoes (Nome_Posicao, Descricao_Posicao) VALUES (%s, %s);", (nome_posicao, descricao_posicao))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('posicoes'))
    return render_template('adicionar_posicoes.html')

# Editar posição
@app.route('/editar_posicao/<int:id>', methods=['GET', 'POST'])
def editar_posicao(id):
    conn = get_db_conn()
    cur = conn.cursor()
    if request.method == 'POST':
        nome_posicao = request.form['nome_posicao']
        descricao_posicao = request.form['descricao_posicao']
        cur.execute("UPDATE Posicoes SET Nome_Posicao = %s, Descricao_Posicao = %s WHERE ID = %s;", (nome_posicao, descricao_posicao, id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('posicoes'))
    cur.execute("SELECT * FROM Posicoes WHERE ID = %s;", (id,))
    posicao = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('editar_posicoes.html', posicao=posicao)

# Remover posição
@app.route('/remover_posicao/<int:id>')
def remover_posicao(id):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM Posicoes WHERE ID = %s;", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('posicoes'))


# Página inicial - lista de sensores
@app.route('/sensores')
def sensores():
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("SELECT s.ID, s.Endereco_ip, m.Nome, p.Nome_Posicao, s.E_Superior FROM Sensores s JOIN Maquinas m ON s.Maquina_ID = m.ID JOIN Posicoes p ON s.Posicao_ID = p.ID;")
    sensores = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index_sensores.html', sensores=sensores)

# Adicionar sensor
@app.route('/adicionar_sensor', methods=['GET', 'POST'])
def adicionar_sensor():
    maquinas = get_maquinas()
    posicoes = get_posicoes()
    if request.method == 'POST':
        endereco_ip = request.form['endereco_ip']
        maquina_id = request.form['maquina']
        posicao_id = request.form['posicao']
        e_superior = 'e_superior' in request.form
        conn = get_db_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO Sensores (Endereco_ip, Maquina_ID, Posicao_ID, E_Superior) VALUES (%s, %s, %s, %s);", (endereco_ip, maquina_id, posicao_id, e_superior))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('sensores'))
    return render_template('adicionar_sensores.html', maquinas=maquinas, posicoes=posicoes)

# Editar sensor
@app.route('/editar_sensor/<int:id>', methods=['GET', 'POST'])
def editar_sensor(id):
    maquinas = get_maquinas()
    posicoes = get_posicoes()
    conn = get_db_conn()
    cur = conn.cursor()
    if request.method == 'POST':
        endereco_ip = request.form['endereco_ip']
        maquina_id = request.form['maquina']
        posicao_id = request.form['posicao']
        e_superior = 'e_superior' in request.form
        cur.execute("UPDATE Sensores SET Endereco_ip = %s, Maquina_ID = %s, Posicao_ID = %s, E_Superior = %s WHERE ID = %s;", (endereco_ip, maquina_id, posicao_id, e_superior, id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('sensores'))
    cur.execute("SELECT * FROM Sensores WHERE ID = %s;", (id,))
    sensor = cur.fetchone()
    cur.close()
    conn.close()
    return render_template('editar_sensores.html', sensor=sensor, maquinas=maquinas, posicoes=posicoes)

# Remover sensor
@app.route('/remover_sensor/<int:id>')
def remover_sensor(id):
    conn = get_db_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM Sensores WHERE ID = %s;", (id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('sensores'))

@app.route('/status')
def status():
    sensors = queries.get_sensors()
    for sensor in sensors:
        sensor_ip = sensor[1]
        distance = fast_get_distance(sensor_ip,8899)
        status = "connected" if distance is not None else "disconnected"
        queries.update_sensor_status(sensor[0], status)
    
    machines = queries.get_machines()
    positions = queries.get_positions()
    sensors = queries.get_sensors()  # Refresh sensor data after updating status
    return render_template('index_status.html', machines=machines, positions=positions, sensors=sensors)


@app.route('/calibrations')
def calibrations():
    machines = queries.get_machines()
    positions = queries.get_positions()
    sensors = queries.get_sensors()
    last_calibrations = queries.get_last_calibration()
    
    calibration_page_data = []
    for machine in machines:
        machine_data = {'machine': machine, 'positions': []}
        for position in positions:
            calibration_data = last_calibrations.get((machine[0], position[0]), None)
            last_calibration_date = "Calibração pendente" if calibration_data is None else calibration_data['date']
            position_data = {'position': position, 'has_sensors': False, 'sensors_connected': True, 'last_calibration': last_calibration_date}
            for sensor in sensors:
                if sensor[2] == machine[0] and sensor[3] == position[0]:
                    position_data['has_sensors'] = True
                    if sensor[5] != 'connected':
                        position_data['sensors_connected'] = False
            machine_data['positions'].append(position_data)
        calibration_page_data.append(machine_data)

    return render_template('calibrations.html', calibration_data=calibration_page_data)



def _run_calibration(machine_id, position_id, block_thickness, timestamp):
    """Run the blocking calibration logic in a background thread.

    Waits for the next ``Medicao`` posted after ``timestamp`` by the measurement
    thread, computes the calibration value and persists it. Updates the entry
    in ``pending_calibrations`` so the polling endpoint can surface progress.
    """
    key = (machine_id, position_id)
    try:
        while True:
            latest_measurement = queries.get_latest_measurement(machine_id, position_id, timestamp)
            if latest_measurement:
                break
            time.sleep(0.5)

        superior_distance = Decimal(latest_measurement[4])
        inferior_distance = Decimal(latest_measurement[5])
        calibration_value = superior_distance + inferior_distance + block_thickness
        queries.insert_calibration((datetime.utcnow(), calibration_value, position_id, machine_id))

        with _state_lock:
            if key in pending_calibrations:
                pending_calibrations[key]['status'] = 'done'
                pending_calibrations[key]['value'] = float(calibration_value)
        logging.info(
            f"Calibration completed for machine {machine_id}, position {position_id}: value={calibration_value}"
        )
    except Exception as exc:  # noqa: BLE001
        logging.exception("Calibration failed for machine %s, position %s", machine_id, position_id)
        with _state_lock:
            if key in pending_calibrations:
                pending_calibrations[key]['status'] = 'error'
                pending_calibrations[key]['error'] = str(exc)


@app.route('/calibrate/<int:machine_id>/<int:position_id>', methods=['GET', 'POST'])
def calibrate(machine_id, position_id):
    if request.method == 'POST':
        block_thickness = Decimal(request.form['block_thickness']).quantize(Decimal('0.00'))
        timestamp = datetime.utcnow()

        logging.info(
            f"Calibration requested for machine {machine_id}, position {position_id} at {timestamp}"
        )

        key = (machine_id, position_id)
        with _state_lock:
            pending_calibrations[key] = {
                'block_thickness': block_thickness,
                'timestamp': timestamp,
                'status': 'waiting',
                'value': None,
                'error': None,
            }

        thread = threading.Thread(
            target=_run_calibration,
            args=(machine_id, position_id, block_thickness, timestamp),
            daemon=True,
        )
        thread.start()

        return render_template(
            'calibrate_progress.html',
            machine_id=machine_id,
            position_id=position_id,
        )

    return render_template('calibrate.html', machine_id=machine_id, position_id=position_id)


@app.route('/calibration_progress/<int:machine_id>/<int:position_id>')
def calibration_progress(machine_id, position_id):
    key = (machine_id, position_id)
    progress = get_reading_progress(machine_id, position_id)
    count = progress.get('count', 0)
    total = progress.get('total', READINGS_PER_CYCLE) or READINGS_PER_CYCLE
    with _state_lock:
        pending = pending_calibrations.get(key, {}).copy()
    status = pending.get('status', 'idle')
    percent = int(round((count / total) * 100)) if status == 'waiting' else 100
    return jsonify({
        'reading_count': count,
        'reading_total': total,
        'status': status,
        'percent': percent,
        'value': pending.get('value'),
        'error': pending.get('error'),
    })

def _parse_month(month_str):
    """Parse a 'YYYY-MM' string into (year, month). Defaults to current month."""
    now_local = datetime.utcnow() + LOCAL_TIME_OFFSET
    if month_str:
        try:
            dt = datetime.strptime(month_str, "%Y-%m")
            return dt.year, dt.month
        except ValueError:
            pass
    return now_local.year, now_local.month


def _month_bounds_local(year, month):
    """Return (start_local, end_local, total_minutes) for the given month.

    Both datetimes are naive local time (UTC-3). ``total_minutes`` is the size
    of the month in minutes.
    """
    start_local = datetime(year, month, 1, 0, 0)
    days_in_month = calendar.monthrange(year, month)[1]
    end_local = start_local + timedelta(days=days_in_month)
    total_minutes = int((end_local - start_local).total_seconds() // 60)
    return start_local, end_local, total_minutes


@app.route('/view_h')
def view_h():
    machines = queries.get_machines()
    positions = queries.get_positions()
    limit_data = limits.load_limits()
    smoothing = limits.load_smoothing()

    machine_data = []

    # New month-based params (preferred); falls back to legacy datetime+hours.
    month_str = request.args.get('month')
    start_min_raw = request.args.get('start_min')
    end_min_raw = request.args.get('end_min')

    year, month = _parse_month(month_str)
    month_start_local, month_end_local, total_minutes = _month_bounds_local(year, month)

    # Previous / next month links
    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    # Week pre-selector: restricts the playground of the trim slider.
    # ``weeks=N`` means the slider can only span [0, N*7days] inside the month.
    week_minutes = 7 * 24 * 60
    days_in_month = (month_end_local - month_start_local).days
    num_weeks = min(5, (days_in_month + 6) // 7)
    try:
        selected_weeks = int(request.args.get('weeks', num_weeks))
    except (TypeError, ValueError):
        selected_weeks = num_weeks
    selected_weeks = max(1, min(num_weeks, selected_weeks))
    week_max_minutes = min(selected_weeks * week_minutes, total_minutes)

    if start_min_raw is not None and end_min_raw is not None:
        try:
            start_min = int(start_min_raw)
            end_min = int(end_min_raw)
        except ValueError:
            start_min, end_min = 0, week_max_minutes
    else:
        # Legacy compatibility: accept datetime + hours if provided
        datetime_str = request.args.get('datetime')
        hours = int(request.args.get('hours', 1))
        if datetime_str:
            start_local = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M")
        else:
            now_local = datetime.utcnow() + LOCAL_TIME_OFFSET
            start_local = now_local - timedelta(hours=hours)
        end_local = start_local + timedelta(hours=hours)
        start_local = max(month_start_local, min(month_end_local, start_local))
        end_local = max(month_start_local, min(month_end_local, end_local))
        start_min = int((start_local - month_start_local).total_seconds() // 60)
        end_min = int((end_local - month_start_local).total_seconds() // 60)

    # Final clamp to the week playground [0, week_max_minutes]
    start_min = max(0, min(week_max_minutes, start_min))
    end_min = max(0, min(week_max_minutes, end_min))
    if end_min < start_min:
        start_min, end_min = end_min, start_min

    start_local = month_start_local + timedelta(minutes=start_min)
    end_local = month_start_local + timedelta(minutes=end_min)

    # Convert local window to UTC for DB queries
    start_time = start_local - LOCAL_TIME_OFFSET
    end_time = end_local - LOCAL_TIME_OFFSET

    for machine in machines:
        machine_id = machine[0]
        machine_graph = limits.get_machine_graph_limits(machine_id, data=limit_data)
        mg_lower = machine_graph['lower']
        mg_upper = machine_graph['upper']

        labels_set_dt = set()
        all_thickness_data = defaultdict(lambda: [None] * len(positions))

        for position_index, position in enumerate(positions):
            position_id = position[0]
            measurements = queries.get_measurements_within_range(machine_id, position_id, start_time, end_time)
            calibrations = queries.get_calibrations(machine_id, position_id)

            calibration_index = 0
            calibration_value = 0

            for measurement in measurements:
                measurement_time = measurement[1]
                while calibration_index < len(calibrations) and calibrations[calibration_index][0] <= measurement_time:
                    calibration_value = calibrations[calibration_index][1]
                    calibration_index += 1

                thickness = calibration_value - measurement[4] - measurement[5]
                all_thickness_data[measurement_time][position_index] = thickness
                labels_set_dt.add(measurement_time)

        labels_dt = sorted(list(labels_set_dt))
        graph_data = [
            (position[1], [all_thickness_data[label][position_index] for label in labels_dt])
            for position_index, position in enumerate(positions)
        ]

        # Smooth first (on raw values), then clamp for display
        graph_data = [
            (name, _smooth_series(labels_dt, vals, smoothing))
            for name, vals in graph_data
        ]
        graph_data = [
            (name, [limits.clamp(v, mg_lower, mg_upper) for v in vals])
            for name, vals in graph_data
        ]

        labels = [(label + LOCAL_TIME_OFFSET).strftime('%d/%m %H:%M:%S') for label in labels_dt]

        machine_data.append({
            'name': machine[1],
            'graph_data': graph_data,
            'labels': labels,
            'limits': limit_data.get(
                str(machine_id),
                {'lower': limits.DEFAULT_LOWER, 'upper': limits.DEFAULT_UPPER},
            ),
            'graph_limits': machine_graph,
        })

    month_label = month_start_local.strftime('%B %Y')

    return render_template(
        'index_view_h.html',
        machines=machine_data,
        month_year=f"{year:04d}-{month:02d}",
        month_label=month_label,
        prev_month=f"{prev_year:04d}-{prev_month:02d}",
        next_month=f"{next_year:04d}-{next_month:02d}",
        total_minutes=total_minutes,
        start_min=start_min,
        end_min=end_min,
        month_start_iso=month_start_local.strftime('%Y-%m-%dT%H:%M'),
        smoothing=smoothing,
        num_weeks=num_weeks,
        selected_weeks=selected_weeks,
        week_max_minutes=week_max_minutes,
        week_minutes=week_minutes,
    )


@app.route('/view')
def view():
    machines = queries.get_machines()
    positions = queries.get_positions()
    limit_data = limits.load_limits()
    smoothing = limits.load_smoothing()

    machine_data = []

    for machine in machines:
        machine_id = machine[0]
        machine_graph = limits.get_machine_graph_limits(machine_id, data=limit_data)
        mg_lower = machine_graph['lower']
        mg_upper = machine_graph['upper']

        labels_set_dt = set()
        all_thickness_data = defaultdict(lambda: [None] * len(positions))

        for position_index, position in enumerate(positions):
            position_id = position[0]
            measurements = queries.get_last_60_minutes_measurements(machine_id, position_id)
            calibrations = queries.get_calibrations(machine_id, position_id)

            calibration_index = 0
            calibration_value = 0

            for measurement in measurements:
                measurement_time = measurement[1]
                while calibration_index < len(calibrations) and calibrations[calibration_index][0] <= measurement_time:
                    calibration_value = calibrations[calibration_index][1]
                    calibration_index += 1

                thickness = calibration_value - measurement[4] - measurement[5]
                all_thickness_data[measurement_time][position_index] = thickness
                labels_set_dt.add(measurement_time)
        
        labels_dt = sorted(list(labels_set_dt))
        graph_data = [
            (position[1], [all_thickness_data[label][position_index] for label in labels_dt])
            for position_index, position in enumerate(positions)
        ]
        machine_limits = limit_data.get(
            str(machine_id),
            {'lower': limits.DEFAULT_LOWER, 'upper': limits.DEFAULT_UPPER},
        )

        time_threshold = datetime.utcnow() - timedelta(seconds=60)

        out_of_limits = False
        # Check out-of-limits against raw (unsmoothed, unclamped) values
        for position_name, thickness_values in graph_data:
            for thickness, timestamp in zip(thickness_values, labels_dt):
                if timestamp > time_threshold and thickness is not None:
                    if thickness < machine_limits['lower'] or thickness > machine_limits['upper']:
                        out_of_limits = True
                        break
            if out_of_limits:
                break 

        # Smooth first, then clamp for display
        graph_data = [
            (name, _smooth_series(labels_dt, vals, smoothing))
            for name, vals in graph_data
        ]
        graph_data = [
            (name, [limits.clamp(v, mg_lower, mg_upper) for v in vals])
            for name, vals in graph_data
        ]

        labels = [(label + LOCAL_TIME_OFFSET).strftime('%H:%M:%S') for label in labels_dt]

        machine_data.append({
            'name': machine[1],
            'graph_data': graph_data,
            'labels': labels,
            'limits': machine_limits,
            'graph_limits': machine_graph,
            'out_of_limits': out_of_limits,
        })

    return render_template('index_view.html', machines=machine_data, smoothing=smoothing)


@app.route('/mobile')
def mobile_view():
    machines = queries.get_machines()
    positions = queries.get_positions()
    limit_data = limits.load_limits()
    smoothing = limits.load_smoothing()

    machine_data = []
    now = datetime.utcnow()

    for machine in machines:
        machine_id = machine[0]
        machine_limits = limit_data.get(
            str(machine_id),
            {'lower': limits.DEFAULT_LOWER, 'upper': limits.DEFAULT_UPPER},
        )
        machine_graph = limits.get_machine_graph_limits(machine_id, data=limit_data)
        mg_lower = machine_graph['lower']
        mg_upper = machine_graph['upper']

        thickness_per_timestamp = defaultdict(list)
        last_15 = []
        last_30 = []
        last_60 = []
        all_values = []
        latest_val = None
        latest_time = None

        for position in positions:
            position_id = position[0]
            measurements = queries.get_last_minutes_measurements(machine_id, position_id, 180)
            calibrations = queries.get_calibrations(machine_id, position_id)

            calibration_index = 0
            calibration_value = 0

            for measurement in measurements:
                m_time = measurement[1]
                while calibration_index < len(calibrations) and calibrations[calibration_index][0] <= m_time:
                    calibration_value = calibrations[calibration_index][1]
                    calibration_index += 1

                thickness = calibration_value - measurement[4] - measurement[5]
                thickness_per_timestamp[m_time].append(thickness)
                all_values.append(thickness)

                if now - m_time <= timedelta(minutes=15):
                    last_15.append(thickness)
                if now - m_time <= timedelta(minutes=30):
                    last_30.append(thickness)
                if now - m_time <= timedelta(minutes=60):
                    last_60.append(thickness)

                if latest_time is None or m_time > latest_time:
                    latest_time = m_time
                    latest_val = thickness

            if not measurements:
                last = queries.get_last_measurement(machine_id, position_id)
                if last:
                    m_time = last[1]
                    calibration_value = 0
                    for cal in calibrations:
                        if cal[0] <= m_time:
                            calibration_value = cal[1]
                        else:
                            break
                    thickness = calibration_value - last[4] - last[5]
                    if latest_time is None or m_time > latest_time:
                        latest_time = m_time
                        latest_val = thickness

        times_15 = sorted([t for t in thickness_per_timestamp if now - t <= timedelta(minutes=15)])
        labels = [(t + LOCAL_TIME_OFFSET).strftime('%H:%M') for t in times_15]
        # Raw averaged series, then smoothing (if enabled), then clamp for display
        raw_values = [
            sum(thickness_per_timestamp[t]) / len(thickness_per_timestamp[t])
            for t in times_15
        ]
        smoothed_values = _smooth_series(times_15, raw_values, smoothing)
        values = [limits.clamp(v, mg_lower, mg_upper) for v in smoothed_values]

        logging.info(
            "Mobile view data for machine %s: labels=%s, values=%s",
            machine_id,
            labels,
            values,
        )

        def avg(lst):
            return sum(lst) / len(lst) if lst else None

        def std(lst):
            m = avg(lst)
            return (sum((x - m) ** 2 for x in lst) / len(lst)) ** 0.5 if lst else None

        avg15 = avg(last_15)
        avg30 = avg(last_30)
        avg60 = avg(last_60)
        avg3h = avg(all_values)
        sd = std(all_values)
        max_v = max(all_values) if all_values else None
        min_v = min(all_values) if all_values else None
        freq = len(last_60) / 60 if last_60 else 0

        sup_count = len([v for v in last_60 if v > machine_limits['upper']])
        inf_count = len([v for v in last_60 if v < machine_limits['lower']])
        perc_inconf = ((sup_count + inf_count) / len(last_60) * 100) if last_60 else 0
        out_limits = False
        if latest_val is not None:
            out_limits = latest_val < machine_limits['lower'] or latest_val > machine_limits['upper']

        machine_data.append({
            'name': machine[1],
            'current': latest_val,
            'labels': labels,
            'values': values,
            'limits': machine_limits,
            'graph_limits': machine_graph,
            'avg15': avg15,
            'avg30': avg30,
            'avg60': avg60,
            'avg3h': avg3h,
            'sup': sup_count,
            'inf': inf_count,
            'perc': perc_inconf,
            'std_dev': sd,
            'max': max_v,
            'min': min_v,
            'freq': freq,
            'out_of_limits': out_limits,
        })

    return render_template('mobile.html', machines=machine_data, smoothing=smoothing)




@app.route('/limits_')
def limits_():
    machines = queries.get_machines()
    limit_data = limits.load_limits()
    graph_limits = limits.load_graph_limits()

    machine_limits = []
    for machine in machines:
        machine_id_str = str(machine[0])
        machine_name = machine[1]
        entry = limit_data.get(machine_id_str, {}) if isinstance(limit_data.get(machine_id_str), dict) else {}
        machine_limits.append({
            'name': machine_name,
            'id': machine[0],
            'lower': entry.get('lower', limits.DEFAULT_LOWER),
            'upper': entry.get('upper', limits.DEFAULT_UPPER),
            'graph_lower': entry.get('graph_lower'),
            'graph_upper': entry.get('graph_upper'),
        })

    return render_template('limits.html', machine_limits=machine_limits, graph_limits=graph_limits)


@app.route('/set_graph_limits', methods=['POST'])
def set_graph_limits():
    lower = request.form.get('graph_lower', type=float)
    upper = request.form.get('graph_upper', type=float)
    if lower is None:
        lower = limits.GRAPH_DEFAULT_LOWER
    if upper is None:
        upper = limits.GRAPH_DEFAULT_UPPER
    limits.save_graph_limits(lower, upper)
    return redirect(url_for('limits_'))


@app.route('/debug')
def debug_page():
    connection_status = False
    table_counts = {}
    sensors = []
    try:
        conn = database.connect()
        connection_status = True
        cur = conn.cursor()
        # Table names in the database are created without quotes and thus are
        # stored in lowercase. ``sql.Identifier`` preserves the case when
        # quoting, so we must use the lowercase names here to avoid errors
        # like ``relation "Maquinas" does not exist`` when querying.
        tables = ['maquinas', 'posicoes', 'sensores', 'calibracoes', 'medicoes']
        for table in tables:
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {};").format(sql.Identifier(table)))
            table_counts[table] = cur.fetchone()[0]
        sensors = queries.get_sensors()
        cur.close()
        conn.close()
    except Exception:
        connection_status = False
        table_counts = {}
        sensors = []
    return render_template('debug.html', sensors=sensors, connection_status=connection_status, table_counts=table_counts)


@app.route('/sensor_reading/<int:sensor_id>')
def sensor_reading(sensor_id):
    sensor = queries.get_sensor(sensor_id)
    value = None
    if sensor:
        ip = sensor[1]
        value = fast_get_distance(ip, 8899)
    return jsonify({'value': value})


@app.route('/set_limits/<machine_id>', methods=['POST'])
def set_limits(machine_id):
    lower = request.form.get('lower_limit', type=float)
    upper = request.form.get('upper_limit', type=float)

    if lower is None:
        lower = limits.DEFAULT_LOWER
    if upper is None:
        upper = limits.DEFAULT_UPPER

    # Per-machine graph scale; empty fields inherit from the global scale
    graph_lower_raw = request.form.get('graph_lower', '').strip()
    graph_upper_raw = request.form.get('graph_upper', '').strip()

    entry = {'lower': lower, 'upper': upper}
    if graph_lower_raw != '':
        try:
            entry['graph_lower'] = float(graph_lower_raw)
        except ValueError:
            pass
    if graph_upper_raw != '':
        try:
            entry['graph_upper'] = float(graph_upper_raw)
        except ValueError:
            pass

    limit_data = limits.load_limits()
    limit_data[str(machine_id)] = entry
    limits.save_limits(limit_data)
    return redirect(url_for('limits_'))


@app.route('/set_smoothing', methods=['POST'])
def set_smoothing():
    enabled = request.form.get('enabled') in ('on', 'true', '1', 'yes')
    try:
        seconds = int(request.form.get('seconds', limits.SMOOTHING_DEFAULT_SECONDS))
    except (TypeError, ValueError):
        seconds = limits.SMOOTHING_DEFAULT_SECONDS
    limits.save_smoothing(enabled, seconds)
    # Redirect back to where the user came from (the graph page)
    referer = request.headers.get('Referer')
    if referer:
        return redirect(referer)
    return redirect(url_for('homepage'))

@app.route('/')
def homepage():
    return render_template('homepage.html')


if __name__ == '__main__':
    # Start the measurement threads (if needed)
    start_measurement_threads()

    # Run the app
    app.run(debug=False, host='0.0.0.0', port=80)
