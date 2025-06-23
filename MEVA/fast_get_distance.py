from pymodbus.client.sync import ModbusTcpClient
import logging

def fast_get_distance(IP_ADDRESS, PORT):
    # Conectando ao servidor MODBUS
    client = ModbusTcpClient(IP_ADDRESS, port=PORT, timeout=1)

    # Se a conexão for bem-sucedida
    if client.connect():
        # Enviando o comando
        # Função: 0x04 (Read Input Registers)
        # Endereço inicial: 0x0000
        # Contagem de registros: 0x0002
        response = client.read_input_registers(address=0x0000, count=2, unit=0x01)

        # Verificando se a resposta é válida
        if response.isError():
            logging.info("Erro na resposta: %s", response)
            return None
        else:
            # Combinando os dois registros de 16 bits
            raw_data = (response.registers[0] << 16) | response.registers[1]

            # Convertendo para uma string de bits
            bits = format(raw_data, '032b')

            # Convertendo de binário para decimal
            decimal_value = int(bits, 2)

            # Convertendo para milímetros
            distance_mm = decimal_value / 1000.0

            # Fechando a conexão
            client.close()

            return distance_mm
    else:
        logging.info("Falha na conexão")
        return None

# Exemplo de uso:
#IP_ADDRESS = '10.10.100.254'
#PORT = 8899
#distance_mm = get_distance(IP_ADDRESS, PORT)
#if distance_mm is not None:
    #print("Distância:", distance_mm, "mm")
#else:
    #print("Não foi possível obter a distância")
