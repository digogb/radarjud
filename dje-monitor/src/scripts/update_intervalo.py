from sqlalchemy import update
from storage.models import PessoaMonitorada
from storage.repository import DiarioRepository
import logging
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    config = Config()
    repo = DiarioRepository(config.database_url)
    
    with repo.SessionLocal() as session:
        stmt = update(PessoaMonitorada).values(intervalo_horas=12)
        result = session.execute(stmt)
        session.commit()
        logger.info(f"Atualizado intervalo para 12h em {result.rowcount} pessoas.")

if __name__ == "__main__":
    main()
