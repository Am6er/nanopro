#! /bin/sh

while true
do
	( sleep 20 ; echo quit ) | sh console.sh
	date
	sleep 600
done
