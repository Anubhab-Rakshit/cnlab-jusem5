#!/bin/bash
# Test Stop and Wait
echo "Testing Stop and Wait"
python3 a2/receiver.py --protocol saw &
REC_PID=$!
sleep 1
python3 a2/sender.py --protocol saw --loss 0.0 --err 0.0 > saw_test.log
kill $REC_PID

# Test Go-Back-N
echo "Testing Go-Back-N"
python3 a2/receiver.py --protocol gbn &
REC_PID=$!
sleep 1
python3 a2/sender.py --protocol gbn --loss 0.0 --err 0.0 > gbn_test.log
kill $REC_PID

# Test Selective Repeat
echo "Testing Selective Repeat"
python3 a2/receiver.py --protocol sr &
REC_PID=$!
sleep 1
python3 a2/sender.py --protocol sr --loss 0.0 --err 0.0 > sr_test.log
kill $REC_PID

echo "Done"
