import os
import sqlite3
import tempfile


class ProgresoManager:
    """Gestiona la base de datos SQLite en una sola clase unificada para progreso."""
    def __init__(self):
        # Utiliza una ruta en el directorio temporal para el archivo de DB
        self.db_path = os.path.join(tempfile.gettempdir(), 'EASYDEPLOY_progreso.db')
        self.init_db()

    def init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            # Tabla simple de clave/valor
            c.execute('CREATE TABLE IF NOT EXISTS data (key TEXT PRIMARY KEY, value TEXT)')
            conn.commit()

    def guardar(self, key, value):
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute('INSERT OR REPLACE INTO data (key, value) VALUES (?, ?)', (str(key), str(value)))
                conn.commit()
        except Exception as e:
            # En un entorno real, esto se loguearía de forma más robusta.
            print(f"Error DB al guardar: {e}")

    def cargar(self, key, default=0):
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute('SELECT value FROM data WHERE key = ?', (str(key),))
                row = c.fetchone()
            return row[0] if row else default
        except Exception:
            return default
