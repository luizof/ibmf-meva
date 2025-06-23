from pymodbus.client.sync import ModbusTcpClient
from time import sleep
import time
from datetime import datetime
import logging

def get_distance(IP_ADDRESS, PORT):
    start_time = time.time()
    # Conectando ao servidor MODBUS
    client = ModbusTcpClient(IP_ADDRESS, port=PORT)

    # Lista para armazenar as distâncias obtidas
    distances = []

    # Tente estabelecer uma conexão
    try:
        # Se a conexão for bem-sucedida
        if client.connect():
            errors = 0
            for _ in range(26):
                time.sleep(0.03)
                # Enviando o comando
                response = client.read_input_registers(address=0x0000, count=2, unit=0x01)

                # Verificando se a resposta é válida
                if response.isError():
                    print("Erro na resposta:", response)
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
            print("conexão fechada, 80 tentativas e ")
            print(errors)
            print(" erros.")
            # Se houve mais de um certo número de erros, pode ser melhor retornar None ou algum tipo de aviso
            if errors > 25:  # Escolhendo 3 como um limite arbitrário
                print("Muitos erros nas leituras!")
                return None

            # Removendo um percentual das leituras nas extremidades
            num_to_remove = int((1/4) * len(distances))  # Removendo 40% dos valores (20% top + 20% buttom)
            for _ in range(num_to_remove):
                distances.remove(max(distances))
                distances.remove(min(distances))

            # Calculando a média das distâncias restantes
            average_distance = sum(distances) / len(distances)
            print("Retornando Distância Bruta do Sensor: ", average_distance, "mm. No IP: ", IP_ADDRESS, " no momento: ", datetime.now()," com ",len(distances),"/26 leituras")
            logging.info(
                f"get_distance success for {IP_ADDRESS} in {time.time() - start_time:.2f}s"
            )
            return average_distance

        else:
            logging.warning(
                f"Falha na conexão com {IP_ADDRESS} após {time.time() - start_time:.2f}s"
            )
            print("Falha na conexão")
            return None

    except Exception as e:  # Captura qualquer exceção
        logging.error(
            f"Erro ao tentar obter a distância de {IP_ADDRESS}: {e}. Tempo decorrido {time.time() - start_time:.2f}s"
        )
        print(f"Erro ao tentar obter a distância: {e}")
        return None



# Exemplo de uso:
#IP_ADDRESS = '10.10.100.254'
#PORT = 8899
#distance_mm = get_distance(IP_ADDRESS, PORT)
#if distance_mm is not None:
    #print("Distância:", distance_mm, "mm")
#else:
    #print("Não foi possível obter a distância")
