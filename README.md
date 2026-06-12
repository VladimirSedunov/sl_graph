# sl_graph
Автотесты для ПО SL_Graph (ПО предназначено для обработки медиапотоков цифрового телевидения)

Приведён код только одного набора тестов.
- Получить список всех имеющихся плат на сервере
- Создать граф, добавить входящий и исходящий девайсы, создать их сопряжение и запустить граф.
- Create graph + add input SDI device + encoder AVC + addOutput device + connect Input to Encoder + Encoder to Output and start
- То же самое, но граф не создаётся, а импортируется.
- То же самое, граф не создаётся, а импортируется. Затем проверяется, что граф стартовал (перейдёт в состояние Running). Затем граф останавливается, экспортируется, полученный JSON сравнивается с исходным.
- set_board_io_config - на плате FD788 поменять входы/выходы IIIIOOOO -> OOOOIIII и обратно.
    Для выполнения теста в исполняемом файле run_tests_sedunov_branch.sh проброшен device sys-forward командой:
    sudo lxc config device add pytestsedunovbranch sys-forward disk source=/sys/class/forward/fd788-${BOARD_NUMBER}
    path=/mnt/forward/fd788-${BOARD_NUMBER}
    В коде автотеста редактируется конфигурационный файл io_config (метод bash_edit_io_config), затем выполняется stub_board.set_board_io_config
