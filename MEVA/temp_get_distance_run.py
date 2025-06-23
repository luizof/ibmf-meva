from pymodbus.client.sync import ModbusTcpClient
import logging

def get_distance(IP_ADDRESS, PORT):
    # Conectando ao servidor MODBUS
    client = ModbusTcpClient(IP_ADDRESS, port=PORT, timeout=1)

    # Lista para armazenar as distâncias obtidas
    distances = []

    # Se a conexão for bem-sucedida
    if client.connect():
        errors = 0
        for _ in range(12):
            # Enviando o comando
            response = client.read_input_registers(address=0x0000, count=2, unit=0x01)

            # Verificando se a resposta é válida
            if response.isError():
                logging.info("Erro na resposta: %s", response)
                errors += 1
                continue
            else:
                # Combinando os dois registros de 16 bits
                raw_data = (response.registers[0] << 16) | response.registers[1]

                # Convertendo para uma string de bits
                bits = format(raw_data, '032b')

                # Convertendo de binário para decimal
                decimal_value = int(bits, 2)

                # Convertendo para milímetros
                distance_mm = decimal_value / 1000.0

                # Adicionando à lista de distâncias
                distances.append(distance_mm)

        # Fechando a conexão
        client.close()

        # Se houve mais de um certo número de erros, pode ser melhor retornar None ou algum tipo de aviso
        if errors > 3:  # Escolhendo 3 como um limite arbitrário
            logging.info("Muitos erros nas leituras!")
            return None

        # Removendo um percentual das leituras nas extremidades
        num_to_remove = int((1/6) * len(distances))  # Removendo 40% dos valores (20% top + 20% buttom)
        for _ in range(num_to_remove):
            distances.remove(max(distances))
            distances.remove(min(distances))

        # Calculando a média das distâncias restantes
        average_distance = sum(distances) / len(distances)

        return average_distance

    else:
        logging.info("Falha na conexão")
        return None


# Exemplo de uso:
IP_ADDRESS = '192.168.1.182'
PORT = 8899
distance_mm = get_distance(IP_ADDRESS, PORT)
if distance_mm is not None:
    logging.info("Distância: %s mm", distance_mm)
else:
    logging.info("Não foi possível obter a distância")
