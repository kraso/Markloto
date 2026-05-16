-- Base de datos histórica de sorteos (Euromillones, Bonoloto, La Primitiva)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sorteos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    juego TEXT NOT NULL CHECK (juego IN ('euromillones', 'bonoloto', 'primitiva')),
    fecha TEXT NOT NULL,
    dia_semana TEXT,
    numero_sorteo INTEGER,
    premio_bote TEXT,
    id_externo TEXT,
    metadata_json TEXT,
    fuente TEXT,
    UNIQUE (juego, fecha)
);

CREATE TABLE IF NOT EXISTS numeros_sorteo (
    sorteo_id INTEGER NOT NULL REFERENCES sorteos (id) ON DELETE CASCADE,
    tipo TEXT NOT NULL CHECK (tipo IN ('principal', 'complementario', 'estrella', 'reintegro')),
    orden INTEGER NOT NULL,
    valor INTEGER NOT NULL,
    PRIMARY KEY (sorteo_id, tipo, orden)
);

CREATE INDEX IF NOT EXISTS idx_sorteos_juego_fecha ON sorteos (juego, fecha);
CREATE INDEX IF NOT EXISTS idx_sorteos_juego ON sorteos (juego);
