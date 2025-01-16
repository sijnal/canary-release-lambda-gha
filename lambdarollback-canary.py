import boto3
import re

def lambda_handler(event, context):
    lambda_client = boto3.client('lambda')
    logs_client = boto3.client('logs')
    events_client = boto3.client('events')

    # Parámetros recibidos del evento
    stable_version = event['stable_version']
    function_name = event['function_name']
    new_version = event['new_version']
    alias_name = event['alias_name']

    log_group_name = f"/aws/lambda/{function_name}"
    print("nombre del grupo: ", log_group_name)
    try:    
        try:
            log_streams = logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=5
             )
            print("logs:", log_streams)

            if 'logStreams' not in log_streams or len(log_streams['logStreams']) == 0:
                print("No logs found for the function.")
                return
        except logs_client.exceptions.ClientError as e:
            print(f"Error al obtener los logs: {str(e)}")
            return

        log_events = []
        found_match = False
        # Buscar en los log streams el que contenga el número dentro de los corchetes
        for log_stream in log_streams['logStreams']:
            log_stream_name = log_stream['logStreamName']
            print(log_stream_name)
                
            # Usar una expresión regular para encontrar el número dentro de los corchetes
            match = re.search(r'\[(\d+)\]', log_stream_name)
            if match:
                # Obtener el número dentro de los corchetes
                log_version = match.group(1)
                print(log_version)
                    
                # Compara si el número coincide con la versión que buscas
                if log_version == new_version:
                    print(f"Log stream {log_stream_name} matches the version {new_version}.")
                    found_match = True
                        
                    # Obtener los eventos del log stream
                    log_events = logs_client.get_log_events(
                        logGroupName=log_group_name,
                        logStreamName=log_stream_name
                    )
                
            if not found_match:
                print(f"No log stream found for version {new_version}.")
                return
            
            error_count = sum(1 for event in log_events['events'] if "ERROR" in event['message'])
            print(f"Errores detectados en la versión {new_version}: {error_count}")

            if error_count > 0:
                # Si hay errores, realizar rollback
                print("Se detectaron más de 1 error. Realizando rollback a la versión estable...")
                lambda_client.update_alias(
                    FunctionName=function_name,
                    Name=alias_name,
                    FunctionVersion=stable_version,
                    RoutingConfig={"AdditionalVersionWeights": {}}
                )
                print("Rollback completado.")
                
                # Desactivar EventBridge Rule
                events_client.disable_rule(Name="CanaryDeploymentScheduledRule")
                print("EventBridge Rule desactivada.")
                return
            else:
                # Tráfico al 100%, finalizar Canary Deployment
                print("Tráfico completamente dirigido a la nueva versión. Canary Deployment exitoso.")
                lambda_client.update_alias(
                    FunctionName=function_name,
                    Name=alias_name,
                    FunctionVersion=new_version,
                    RoutingConfig={"AdditionalVersionWeights": {}}
                )

                # Desactivar EventBridge Rule
                events_client.disable_rule(Name="CanaryDeploymentScheduledRule")
                print("EventBridge Rule desactivada.")

    except Exception as e:
        print(f"Error durante el proceso de Canary Deployment: {str(e)}")
        raise e

