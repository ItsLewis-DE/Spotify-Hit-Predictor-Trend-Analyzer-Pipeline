# =============================================================================
# Custom Airflow Image
# =============================================================================
# Pre-installs all Python dependencies at build time to avoid:
#   1. Slow container startup from runtime pip installs
#   2. cffi version conflict: snowflake-connector-python requires cffi<2.0.0
#      but PyNaCl 1.6.2 (in base image) was compiled against cffi 2.0.0
# =============================================================================
FROM apache/airflow:3.2.2-python3.12

USER airflow

# Install additional Python packages
# NOTE: We install snowflake-connector-python first (which downgrades cffi),
# then force-reinstall cffi>=2.0.0 to maintain binary compatibility with
# PyNaCl in the base image.
RUN pip install --no-cache-dir \
    selenium \
    webdriver-manager \
    awscli \
    dbt-snowflake \
    snowflake-connector-python \
    && pip install --no-cache-dir --force-reinstall "cffi>=2.0.0"
