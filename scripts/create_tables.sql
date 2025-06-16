\connect BD_MEP

CREATE TABLE IF NOT EXISTS Maquinas (
    ID SERIAL PRIMARY KEY,
    Nome VARCHAR(255),
    Descricao TEXT
);

CREATE TABLE IF NOT EXISTS Posicoes (
    ID SERIAL PRIMARY KEY,
    Nome_Posicao VARCHAR(255),
    Descricao_Posicao TEXT
);

CREATE TABLE IF NOT EXISTS Sensores (
    ID SERIAL PRIMARY KEY,
    Endereco_ip VARCHAR(255),
    Maquina_ID INTEGER REFERENCES Maquinas(ID),
    Posicao_ID INTEGER REFERENCES Posicoes(ID),
    E_Superior BOOLEAN,
    status VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS Calibracoes (
    ID SERIAL PRIMARY KEY,
    Data_Hora_Calibracao TIMESTAMP,
    Valor_Distancia FLOAT,
    Posicao_ID INTEGER REFERENCES Posicoes(ID)
);

CREATE TABLE IF NOT EXISTS Medicoes (
    ID SERIAL PRIMARY KEY,
    Data_Hora TIMESTAMP,
    Maquina_ID INTEGER REFERENCES Maquinas(ID),
    Posicao_Leitura_ID INTEGER REFERENCES Posicoes(ID),
    Valor_Medicao_Superior FLOAT,
    Valor_Medicao_Inferior FLOAT
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns 
        WHERE table_name='calibracoes' 
        AND column_name='maquina_id'
    ) THEN
        ALTER TABLE Calibracoes
        ADD COLUMN maquina_id INTEGER;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.table_constraints 
        WHERE constraint_name='fk_maquina_id'
    ) THEN
        ALTER TABLE Calibracoes
        ADD CONSTRAINT fk_maquina_id
        FOREIGN KEY (maquina_id) REFERENCES Maquinas(ID);
    END IF;
END $$;
