# dados de conexão com o mysql
# pode mexer aqui ou usar variáveis de ambiente (clinica_db_user, clinica_db_password...)
import os

db_config = {
    "host": os.getenv("CLINICA_DB_HOST", "localhost"),
    "user": os.getenv("CLINICA_DB_USER", "root"),
    "password": os.getenv("CLINICA_DB_PASSWORD", ""),
    "port": int(os.getenv("CLINICA_DB_PORT", "3306")),
}
db_name = os.getenv("CLINICA_DB_NAME", "clinica_vet")
