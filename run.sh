#!/bin/bash

trap "exit" INT

for file in ../annotated_cha/annotated_cha/*
do
    python add_pho.py $file
done


