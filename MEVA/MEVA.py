from flask import Flask, jsonify, redirect, render_template, request, url_for
from psycopg2 import sql
from datetime import datetime, timedelta
from decimal import Decimal
from time import sleep
from collections import defaultdict
import concurrent.futures
import logging
import os
import threading
import time
import webbrowser

import config
import database
import limits
import queries
from fast_get_distance import fast_get_distance
from get_distance import get_distance
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)

def measure_sensor_pair(sensor_pair):
    machine_id = sensor_pair[2]
    position_id = sensor_pair[3]
    logging.info(f"Starting measurement thread for machine {machine_id}, position {position_id}")

    superior_distances = []
    inferior_distances = []

    while True:
        superior_ip = sensor_pair[1]
        inferior_ip = sensor_pair[7]

        #print(f"Superior IP: {superior_ip}, Inferior IP: {inferior_ip}") # Imprimir IPs

        # Função auxiliar para obter a distância
        def fetch_distance(ip):
            return get_distance(ip, 8899)

        # Use ThreadPoolExecutor para executar as chamadas de forma paralela
        with concurrent.futures.ThreadPoolExecutor() as executor:
            superior_future = executor.submit(fetch_distance, superior_ip)
            inferior_future = executor.submit(fetch_distance, inferior_ip)

            superior_distance = superior_future.result()
            inferior_distance = inferior_future.result()

        # Adicionar as distâncias às listas
        if superior_distance is not None and inferior_distance is not None:
            superior_distances.append(superior_distance)
            inferior_distances.append(inferior_distance)

        # Se ambas as listas tiverem 5 valores, processe e insira no banco
        if len(superior_distances) >= 11 and len(inferior_distances) >= 11:
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

            timestamp = datetime.now()
            data = (timestamp, machine_id, position_id, superior_avg, inferior_avg)
            queries.insert_measurement(data)
            logging.info(
                f"Measurement inserted for machine {machine_id}, position {position_id}: "
                f"sup={superior_avg:.2f} inf={inferior_avg:.2f}"
            )

            # Limpar as listas para o próximo conjunto de 5 valores
            superior_distances.clear()
            inferior_distances.clear()

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



@app.route('/calibrate/<int:machine_id>/<int:position_id>', methods=['GET', 'POST'])
def calibrate(machine_id, position_id):
    if request.method == 'POST':
        block_thickness = Decimal(request.form['block_thickness']).quantize(Decimal('0.00'))
        timestamp = datetime.now()

        logging.info(
            f"Calibration requested for machine {machine_id}, position {position_id} at {timestamp}"
        )

        # Espere pela próxima entrada de dados
        while True:
            latest_measurement = queries.get_latest_measurement(machine_id, position_id, timestamp)
            if latest_measurement:
                logging.info(
                    f"Measurement found for calibration: sup={latest_measurement[4]} inf={latest_measurement[5]}"
                )
                break
            logging.debug("No measurement yet for calibration, waiting 1s")
            time.sleep(1)

        # Calcule o valor da calibração
        superior_distance = Decimal(latest_measurement[4])
        inferior_distance = Decimal(latest_measurement[5])
        calibration_value = superior_distance + inferior_distance + block_thickness

        # Insira a calibração no banco de dados
        queries.insert_calibration((datetime.now(), calibration_value, position_id, machine_id))

        return render_template('calibration_completed.html')

    return render_template('calibrate.html', machine_id=machine_id, position_id=position_id)

@app.route('/view_h')
def view_h():
    machines = queries.get_machines()
    positions = queries.get_positions()
    limit_data = limits.load_limits()

    machine_data = []
    
    datetime_str = request.args.get('datetime')
    start_time = None
    if datetime_str:
        start_time = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M")
        end_time = start_time + timedelta(minutes=60)

    for machine in machines:
        machine_id = machine[0]

        labels_set_dt = set()
        # Cada timestamp pode ter um valor por posição. Use uma lista do
        # tamanho de ``positions`` para acomodar todas as posições,
        # evitando erros quando houver mais de duas posições cadastradas.
        all_thickness_data = defaultdict(lambda: [None] * len(positions))

        for position_index, position in enumerate(positions):  # Iterate over all positions
            position_id = position[0]
            if start_time and end_time:  # Apenas obter medições se start_time e end_time estiverem definidos
                measurements = queries.get_measurements_within_range(machine_id, position_id, start_time, end_time)
                calibrations = queries.get_calibrations(machine_id, position_id) # Get calibrations ordered by timestamp

                calibration_index = 0
                calibration_value = 0

                for measurement in measurements:
                    measurement_time = measurement[1]
                    # Update the calibration value based on the timestamp
                    while calibration_index < len(calibrations) and calibrations[calibration_index][0] <= measurement_time:
                        calibration_value = calibrations[calibration_index][1]
                        calibration_index += 1

                    thickness = calibration_value - measurement[4] - measurement[5]
                    all_thickness_data[measurement_time][position_index] = thickness
                    labels_set_dt.add(measurement_time)

        labels_dt = sorted(list(labels_set_dt))
        graph_data = [(position[1], [all_thickness_data[label][position_index] for label in labels_dt]) for position_index, position in enumerate(positions)]
        labels = [label.strftime('%H:%M:%S') for label in labels_dt]

        machine_data.append({
            'name': machine[1],
            'graph_data': graph_data,
            'labels': labels,
            'limits': limit_data.get(str(machine_id), {'lower': 1, 'upper': 4}),
        })

    return render_template('index_view_h.html', machines=machine_data)


@app.route('/view')
def view():
    machines = queries.get_machines()
    positions = queries.get_positions()
    limit_data = limits.load_limits()

    machine_data = []

    for machine in machines:
        machine_id = machine[0]

        labels_set_dt = set()
        # ``positions`` pode possuir mais de duas entradas. Inicialize cada
        # timestamp com uma lista do tamanho correto para armazenar a espessura
        # de todas as posições.
        all_thickness_data = defaultdict(lambda: [None] * len(positions))

        for position_index, position in enumerate(positions):  # Iterate over all positions
            position_id = position[0]
            measurements = queries.get_last_60_minutes_measurements(machine_id, position_id)
            calibrations = queries.get_calibrations(machine_id, position_id) # Get calibrations ordered by timestamp

            calibration_index = 0
            calibration_value = 0

            for measurement in measurements:
                measurement_time = measurement[1]
                # Update the calibration value based on the timestamp
                while calibration_index < len(calibrations) and calibrations[calibration_index][0] <= measurement_time:
                    calibration_value = calibrations[calibration_index][1]
                    calibration_index += 1

                thickness = calibration_value - measurement[4] - measurement[5]
                all_thickness_data[measurement_time][position_index] = thickness
                labels_set_dt.add(measurement_time)
        
        labels_dt = sorted(list(labels_set_dt))
        graph_data = [(position[1], [all_thickness_data[label][position_index] for label in labels_dt]) for position_index, position in enumerate(positions)]
        machine_limits = limit_data.get(str(machine_id), {'lower': 1, 'upper': 4})

        time_threshold = datetime.now() - timedelta(seconds=60)

        out_of_limits = False
        
        for position_name, thickness_values in graph_data:
            for thickness, timestamp in zip(thickness_values, labels_dt):
                if timestamp > time_threshold and thickness is not None:
                    if thickness < machine_limits['lower'] or thickness > machine_limits['upper']:
                        out_of_limits = True
                        break

            if out_of_limits:
                break 

        labels = [label.strftime('%H:%M:%S') for label in labels_dt]

        machine_data.append({
            'name': machine[1],
            'graph_data': graph_data,
            'labels': labels,
            'limits': limit_data.get(str(machine_id), {'lower': 1, 'upper': 4}),
            'out_of_limits': out_of_limits,
        })

    return render_template('index_view.html', machines=machine_data)


@app.route('/mobile')
def mobile_view():
    machines = queries.get_machines()
    positions = queries.get_positions()
    limit_data = limits.load_limits()

    machine_data = []
    now = datetime.now()

    for machine in machines:
        machine_id = machine[0]
        machine_limits = limit_data.get(str(machine_id), {'lower': 1, 'upper': 4})

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

        times_15 = sorted([t for t in thickness_per_timestamp if now - t <= timedelta(minutes=15)])
        labels = [t.strftime('%H:%M') for t in times_15]
        values = [sum(thickness_per_timestamp[t]) / len(thickness_per_timestamp[t]) for t in times_15]

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

    return render_template('mobile.html', machines=machine_data)




@app.route('/limits_')
def limits_():
    machines = queries.get_machines()
    limit_data = limits.load_limits()

    machine_limits = []
    for machine in machines:
        machine_id_str = str(machine[0])
        machine_name = machine[1]
        lower_limit = limit_data.get(machine_id_str, {}).get('lower', 'Não definido')
        upper_limit = limit_data.get(machine_id_str, {}).get('upper', 'Não definido')
        machine_limits.append((machine_name, lower_limit, upper_limit, machine[0]))

    return render_template('limits.html', machine_limits=machine_limits)


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


@app.route('/set_limits/<machine_id>/<float:limit>')
def set_limits(machine_id, limit):
    limit_data = limits.load_limits()
    limit_data[machine_id] = {
        'lower': limit - 0.2,
        'upper': limit + 0.2
    }
    limits.save_limits(limit_data)
    return redirect(url_for('limits_'))

@app.route('/')
def homepage():
    return render_template('homepage.html')


def open_urls():
    urls_old = [
        'http://127.0.0.1/maquinas',
        'http://127.0.0.1/posicoes',
        'http://127.0.0.1/sensores',
        'http://127.0.0.1/status',
        'http://127.0.0.1/calibrations',
        'http://127.0.0.1/view_h',
        'http://127.0.0.1/view',
        'http://127.0.0.1/limits_'
    ]

    urls = [
        'http://127.0.0.1/'
    ]

    for url in urls:
        webbrowser.open(url)
        sleep(0.2)


if __name__ == '__main__':
    # Optionally open the web interface when running locally
    if os.environ.get('OPEN_BROWSER_ON_STARTUP') == '1':
        threading.Thread(target=open_urls).start()

    # Start the measurement threads (if needed)
    start_measurement_threads()

    # Run the app
    app.run(debug=False, host='0.0.0.0', port=80)
