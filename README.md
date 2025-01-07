# canary-lambda-gha
Debe exitir la funciona lambda - MyLambdaFunctionCanary
Debe existir una version publicada - 1
Debe existir el alias - prod
o tenerlas en variables de entorno


aws events list-targets-by-rule --rule CanaryDeploymentScheduledRule --query 'Targets[*].[Id,Arn]' --output table
