#!/bin/bash

trap "exit" INT

for file in $1*
do
    echo 'AHAHHAHAHAHAHAHA' $file $PWD
    bas=`basename $file`
    sm=`basename $file | cut -f1,2 -d'_'`
    echo $sm
    echo $sm/$bas
    mkdir $sm
    python add_pho.py $file --output $sm/$bas.bak
done


