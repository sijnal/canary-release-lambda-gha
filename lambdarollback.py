import boto3
import re

def lambda_handler(event, context):
    lambda_client = boto3.client('lambda')
    logs_client = boto3.client('logs')
    events_client = boto3.client('events')

    # Parámetros recibidos del evento
    stable_version = event['stable_version']
    function_name = event['function_name']
    new_version = event['new_version']  # Versión que se desea probar
    traffic_increment = 0.1  # Incremento del tráfico (en %)

    log_group_name = f"/aws/lambda/{function_name}"
    print("nombre del grupo: ", log_group_name)
    try:
        # Obtener RoutingConfig del alias 'prod' de la lambda
        alias_response = lambda_client.get_alias(
            FunctionName=function_name,
            Name='prod'
        )
        print("datos del alias:", alias_response)

        routing_config = alias_response.get('RoutingConfig', {"AdditionalVersionWeights": {}})
        print("versiones adicional en el alias:", routing_config)

        # Validar tráfico actual para la nueva versión
        current_traffic = routing_config.get("AdditionalVersionWeights", {}).get(new_version, 0)
        print("trafico inicial:", current_traffic)

        if current_traffic < 0.9:
            print("trafico:", current_traffic)
            
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

            if error_count > 1:
                # Si hay errores, realizar rollback
                print("Se detectaron más de 1 error. Realizando rollback a la versión estable...")
                lambda_client.update_alias(
                    FunctionName=function_name,
                    Name='prod',
                    FunctionVersion=stable_version,
                    RoutingConfig={"AdditionalVersionWeights": {}}
                )
                print("Rollback completado.")
                
                # Desactivar EventBridge Rule
                events_client.disable_rule(Name="CanaryDeploymentScheduledRule")
                print("EventBridge Rule desactivada.")
                return

            # Incrementar tráfico en 10%
            current_traffic = routing_config["AdditionalVersionWeights"][new_version]
            new_traffic = round(current_traffic + traffic_increment, 1)
            routing_config["AdditionalVersionWeights"][new_version] = new_traffic
            
            lambda_client.update_alias(
                FunctionName=function_name,
                Name='prod',
                FunctionVersion=stable_version,
                RoutingConfig=routing_config
            )
            print(f"Incrementado tráfico hacia la versión {new_version}: {int(new_traffic * 100)}%.")
        else:
            # Tráfico al 100%, finalizar Canary Deployment
            print("Tráfico completamente dirigido a la nueva versión. Canary Deployment exitoso.")
            lambda_client.update_alias(
                FunctionName=function_name,
                Name='prod',
                FunctionVersion=new_version,
                RoutingConfig={"AdditionalVersionWeights": {}}
            )

            # Desactivar EventBridge Rule
            events_client.disable_rule(Name="CanaryDeploymentScheduledRule")
            print("EventBridge Rule desactivada.")

    except Exception as e:
        print(f"Error durante el proceso de Canary Deployment: {str(e)}")
        raise e

