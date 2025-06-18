from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock
from pymodbus.datastore import ModbusSlaveContext, ModbusServerContext
import config

# Definindo o valor que será retornado (50.0mm)
value_to_return_mm = 50.0

# Convertendo o valor em um valor inteiro de 32 bits
value_to_return_int = int(value_to_return_mm * 0.01)

# Dividindo o valor inteiro de 32 bits em dois registros de 16 bits
register1 = (value_to_return_int >> 16) & 0xFFFF
register2 = value_to_return_int & 0xFFFF

# Criando o bloco de dados com os valores definidos
# Incluindo mais registros para cobrir uma faixa maior
block = ModbusSequentialDataBlock(0x0000, [register1, register2] + [0] * 100)

# Definindo o contexto com os valores
# Usando o bloco apenas para os registros de entrada (ir)
store = ModbusSlaveContext(ir=block)
context = ModbusServerContext(slaves=store, single=True)
# Porta para o servidor escutar
port = config.SENSOR_PORT

# Iniciando o servidor na porta especificada
StartTcpServer(context, address=("0.0.0.0", port))
