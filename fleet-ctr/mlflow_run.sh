#!/bin/bash
if [[  $PADDLE_TRAINER_ID -ne 0 ]] ; then
    echo "PADDLE_TRAINER_ID unset or Run MLFlow on Trainer 0."
    exit 0
fi

while true ; do
echo "Still wait for CTR Training Setup"
sleep 10
if [ -d  "./mlruns/0" ] ;then
    mlflow server --default-artifact-root ./mlruns/0 --host 0.0.0.0 --port 8111
fi
done
exit 0
