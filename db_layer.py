import os
import pandas as pd
from databricks import sql
from dotenv import load_dotenv

load_dotenv()

class DatabricksConnectionManager:
    """Manages the lifecycle of a connection to Databricks SQL Warehouse."""
    def __init__(self):
        self.server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME")
        self.http_path = os.getenv("DATABRICKS_HTTP_PATH")
        self.access_token = os.getenv("DATABRICKS_ACCESS_TOKEN")
        self._connection = None

        if not all([self.server_hostname, self.http_path, self.access_token]) or "your-warehouse-id" in str(self.http_path):
            raise ValueError("Missing or unconfigured Databricks credentials in environment variables.")

    def connect(self):
        if not self._connection:
            try:
                self._connection = sql.connect(
                    server_hostname=self.server_hostname,
                    http_path=self.http_path,
                    access_token=self.access_token
                )
            except Exception as e:
                raise RuntimeError(f"Error establishing Databricks connection: {e}")
        return self._connection

    def close(self):
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            finally:
                self._connection = None


class DatabricksQueryExecutor:
    """Handles execution of SQL queries and converts outputs to DataFrames."""
    def __init__(self, connection_manager: DatabricksConnectionManager):
        self.connection_manager = connection_manager

    def execute_to_dataframe(self, query: str, params: tuple = None) -> pd.DataFrame:
        """Executes a SQL query and returns result directly as a clean Pandas DataFrame."""
        connection = self.connection_manager.connect()
        cursor = connection.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            raw_data = cursor.fetchall()

            if cursor.description:
                columns = [col[0] for col in cursor.description]
                data_dicts = [dict(zip(columns, row)) for row in raw_data]
                return pd.DataFrame(data_dicts)
            return pd.DataFrame()
        except Exception as e:
            raise RuntimeError(f"Database query operation failed: {e}")
        finally:
            cursor.close()

    def lookup_seller_by_id(self, seller_id: str) -> pd.DataFrame:
        seller_id = seller_id.strip()
        query = """
            SELECT seller_key, seller_id, name, type, seller_tier
            FROM `workspace`.`tijartek_gold`.`dim_seller`
            WHERE seller_id = ?
            LIMIT 10;
        """
        return self.execute_to_dataframe(query, params=(seller_id,))

    def lookup_seller_by_name(self, name: str) -> pd.DataFrame:
        name = f"%{name.strip()}%"
        query = """
            SELECT seller_key, seller_id, name, type, seller_tier
            FROM `workspace`.`tijartek_gold`.`dim_seller`
            WHERE name LIKE ?
            LIMIT 10;
        """
        return self.execute_to_dataframe(query, params=(name,))

    def lookup_seller_combined(self, name: str, seller_id: str) -> pd.DataFrame:
        name = f"%{name.strip()}%"
        seller_id = seller_id.strip()
        query = """
            SELECT seller_key, seller_id, name, type, seller_tier
            FROM `workspace`.`tijartek_gold`.`dim_seller`
            WHERE seller_id = ? AND name LIKE ?
            LIMIT 10;
        """
        return self.execute_to_dataframe(query, params=(seller_id, name))