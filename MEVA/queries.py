from database import connect

def get_machines():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Maquinas;")
    machines = cur.fetchall()
    conn.close()
    return machines

def get_measurements_within_range(machine_id, position_id, start_time, end_time):
    conn = connect()
    cur = conn.cursor()
    query = """
        SELECT * FROM Medicoes
        WHERE Maquina_ID = %s AND Posicao_Leitura_ID = %s AND Data_Hora BETWEEN %s AND %s
        ORDER BY Data_Hora;
    """
    cur.execute(query, (machine_id, position_id, start_time, end_time))
    result = cur.fetchall()
    conn.close()
    return result


def get_last_60_minutes_measurements(machine_id, position_id):
    conn = connect()
    cur = conn.cursor()
    query = """
        SELECT ID, date_trunc('second', Data_Hora), Maquina_ID, Posicao_Leitura_ID, Valor_Medicao_Superior, Valor_Medicao_Inferior 
        FROM Medicoes
        WHERE Maquina_ID = %s AND Posicao_Leitura_ID = %s AND Data_Hora > NOW() - INTERVAL '60 minutes'
        ORDER BY Data_Hora ASC;
    """
    cur.execute(query, (machine_id, position_id))
    result = cur.fetchall()
    conn.close()
    return result


def get_calibrations(machine_id, position_id):
    conn = connect()
    cur = conn.cursor()
    query = """
        SELECT Data_Hora_Calibracao, Valor_Distancia
        FROM Calibracoes
        WHERE Maquina_ID = %s AND Posicao_ID = %s
        ORDER BY Data_Hora_Calibracao ASC;
    """
    cur.execute(query, (machine_id, position_id))
    calibrations = cur.fetchall()
    conn.close()
    return calibrations


def get_last_calibration():
    conn = connect()
    cur = conn.cursor()
    query = """
        SELECT m.Maquina_ID, c.Posicao_ID, MAX(c.Data_Hora_Calibracao) as last_calibration_date, c.Valor_Distancia
        FROM Calibracoes AS c
        JOIN Medicoes AS m ON c.Posicao_ID = m.Posicao_Leitura_ID AND c.Maquina_ID = m.Maquina_ID
        WHERE c.Data_Hora_Calibracao = (
            SELECT MAX(c2.Data_Hora_Calibracao)
            FROM Calibracoes AS c2
            WHERE c2.Posicao_ID = c.Posicao_ID AND c2.Maquina_ID = c.Maquina_ID
        )
        GROUP BY m.Maquina_ID, c.Posicao_ID, c.Valor_Distancia;
    """
    cur.execute(query)
    last_calibrations = {(row[0], row[1]): {'date': row[2], 'value': row[3]} for row in cur.fetchall()}
    conn.close()
    return last_calibrations





def get_latest_measurement(machine_id, position_id, timestamp):
    conn = connect()
    cur = conn.cursor()
    query = """
        SELECT * FROM Medicoes
        WHERE Maquina_ID = %s AND Posicao_Leitura_ID = %s AND Data_Hora > %s
        ORDER BY Data_Hora DESC
        LIMIT 1;
    """
    cur.execute(query, (machine_id, position_id, timestamp))
    result = cur.fetchone()
    conn.close()
    return result

def insert_calibration(data):
    conn = connect()
    cur = conn.cursor()
    query = "INSERT INTO Calibracoes (Data_Hora_Calibracao, Valor_Distancia, Posicao_ID, Maquina_ID) VALUES (%s, %s, %s, %s);"
    cur.execute(query, data)
    conn.commit()
    conn.close()


def get_positions():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Posicoes;")
    positions = cur.fetchall()
    conn.close()
    return positions

def get_sensors():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT * FROM Sensores;")
    sensors = cur.fetchall()
    conn.close()
    return sensors

def get_sensor_pairs():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT s1.*, s2.*
        FROM Sensores AS s1
        JOIN Sensores AS s2 ON s1.Maquina_ID = s2.Maquina_ID AND s1.Posicao_ID = s2.Posicao_ID
        WHERE s1.E_Superior = TRUE AND s2.E_Superior = FALSE;
    """)
    sensor_pairs = cur.fetchall()
    conn.close()
    return sensor_pairs

def insert_measurement(data):
    conn = connect()
    cur = conn.cursor()
    query = """
        INSERT INTO Medicoes (Data_Hora, Maquina_ID, Posicao_Leitura_ID, Valor_Medicao_Superior, Valor_Medicao_Inferior)
        VALUES (%s, %s, %s, %s, %s);
    """
    cur.execute(query, data)
    conn.commit()
    conn.close()

def update_sensor_status(sensor_id, status):
    conn = connect()
    cur = conn.cursor()
    query = "UPDATE Sensores SET status = %s WHERE ID = %s;"
    cur.execute(query, (status, sensor_id))
    conn.commit()
    conn.close()
