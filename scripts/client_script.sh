#!/bin/bash

expConfig=$1
logName=$2
bin=$3

sleep 10
$3 -c $expConfig -l $logName -s 123
