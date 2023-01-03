config = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'app_mitgliederportal',
    'password': '46TdG4DNCW4SDNTH',
    'database': 'mitgliederportal'
}

pool_config = config | {
    'pool_name': 'web-app'
}