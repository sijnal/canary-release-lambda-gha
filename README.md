# canary-lambda-gha
Debe exitir la funciona lambda - MyLambdaFunctionCanary
Debe existir una version publicada - 1
Debe existir el alias - prod
o tenerlas en variables de entorno


aws lambda add-permission \
            --function-name Rollbacklambdacanary \
            --principal events.amazonaws.com \
            --statement-id SomeUniqueID \
            --action "lambda:InvokeFunction"z