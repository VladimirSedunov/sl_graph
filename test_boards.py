import inspect
import json
import os
from time import sleep

import pytest
from colorama import Fore
from deepdiff import DeepDiff

import subprocess

from sl_device_types_pb2 import SLDeviceProto, SLConfiguratorInfoProto
from sl_graph_types_pb2 import SLEmptyProto, SLEncoderSupportProto
from sl_graph_types_pb2 import SLGraphProto, SLGraphTypeProto, SLGraphDeviceProto, SLInputProgramListProto, SLOutputProgramProto, \
    SLGraphOutputProgramProto, SLGraphProgramEncoderProto, SLStreamProto, SLStreamTypeProto, SLEncoderProto, SLVideoEncoderTypeProto, \
    SLAudioEncoderTypeProto, SLInputProgramProto, \
    SLGraphEncoderDeviceProto, SLGraphStringProto
from sl_py_tests.helpers.json_diff import analyze_deep_diff
from sl_py_tests.helpers.procs import helper_wait_graph_created, helper_delete_graph_by_name, helper_stop_graph, helper_start_graph, \
    helper_get_graph_by_name, helper_import_graph, helper_get_input_device_by_name, helper_get_input_program_list, \
    helper_connect_input_to_output, helper_add_output_device_to_graph, helper_add_input_device_to_graph, \
    helper_get_graph_input_device_by_configurator_info, helper_get_input_program_first, helper_get_encoder_from_program_first, \
    helper_get_output_program_from_encoder_first, helper_get_graph_output_device_first, helper_delete_graph
from sl_py_tests.helpers.proverki import print_test_result
from sl_py_tests.proj_set import project_settings
from sl_py_tests.tests.sl_board_server_pb2 import SLBoards, SLBoardIOConfig, SLIOConfig, SLPinDirection, SLGenlockState, \
    SLBoardGenlock, SLGenlock
from sl_py_tests.tests.test_licences import helper_read_dict_from_json


def test_get_available_boards_T6TC1(get_stub_board):
    """ 1. Получить список всех имеющихся плат """
    print(f'\nT6TC1:   Получить список всех имеющихся плат')
    test_ok = True
    stub_board = get_stub_board
    slboards: SLBoards = stub_board.get_available_boards(SLEmptyProto())
    list_boards = slboards.list
    for b in list_boards:
        print(b)
    print_test_result(test_ok, inspect.currentframe().f_code.co_name)


def test_T6TC2(get_stub):
    """
    Create graph + add input SDI device + add output SDI device.
    Connect Input to Output and Start.
    Ждём, когда граф перейдёт в состояние Running
    """

    print(f'\nT6TC2:   Create graph + add input SDI device + add output SDI device. Connect Input to Output and Start.')
    test_ok = True

    stub = get_stub
    new_graph_name = 'Автотест T6TC2'

    if not helper_delete_graph_by_name(stub=stub, graph_name=new_graph_name):
        print(f'❌ Не удалось удалить граф {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    graph_to_create = SLGraphProto(name=new_graph_name, guid=None, state=None, host=project_settings.host_grpc,
                                   port=0, type=SLGraphTypeProto.sl_encoder_decoder, alarm=None)
    stub.create_graph(graph_to_create)

    created, graph = helper_wait_graph_created(stub=stub, graph_name=new_graph_name)
    if not created:
        print(f'❌ Не удалось создать граф {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    helper_stop_graph(stub=stub, graph=graph)

    added_input_device = helper_add_input_device_to_graph(stub=stub, graph=graph, device_name='FD SDI Capture')
    added_output_device = helper_add_output_device_to_graph(stub=stub, graph=graph, device_name='FD SDI Renderer')

    in_prog_list: SLInputProgramListProto = helper_get_input_program_list(stub=stub, graph=graph, device=added_input_device)
    if not len(in_prog_list.list) > 0:
        print(f'❌ Не найдены input programs')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    input_program = in_prog_list.list[0]
    helper_connect_input_to_output(stub=stub, graph=graph, output_device=added_output_device, input_program=input_program, name_number_provider=62)

    test_ok &= is_graph_running(graph=graph, stub=stub)
    if not test_ok:
        print(f'❌ Статус графа {new_graph_name} не равен "Running"')

    if not helper_delete_graph(stub=stub, graph=graph):
        print(f'❌ Не удалось удалить граф {new_graph_name}')
        test_ok = False
    print_test_result(test_ok, inspect.currentframe().f_code.co_name)


def test_T6TC3(get_stub):
    """
    Create graph + add input SDI device + encoder AVC + add Output device + connect Input to Encoder + Encoder to Output and start
    Ждём, когда граф перейдёт в состояние Running
    """

    print(f'\nT6TC3:  Create graph + add input SDI device + encoder AVC + addOutput device + connect Input to Encoder + Encoder to Output and start.')
    test_ok = True

    stub = get_stub
    new_graph_name = 'Автотест T6TC3'

    if not helper_delete_graph_by_name(stub=stub, graph_name=new_graph_name):
        print(f'❌ Не удалось удалить граф {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    graph_to_create = SLGraphProto(name=new_graph_name, guid=None, state=None, host=project_settings.host_grpc,
                                   port=0, type=SLGraphTypeProto.sl_encoder_decoder, alarm=None)
    stub.create_graph(graph_to_create)
    created, graph = helper_wait_graph_created(stub=stub, graph_name=new_graph_name)
    if not created:
        print(f'❌ Не удалось создать граф {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    helper_stop_graph(stub=stub, graph=graph)

    input_sdi_device = helper_get_input_device_by_name(stub=stub, name='FD SDI Capture')
    configurator_info: SLConfiguratorInfoProto = input_sdi_device.configurator_info
    added_input_device = add_custom_input_device_to_graph(stub=stub, graph=graph, input_sdi_device=input_sdi_device)
    added_output_device = helper_add_output_device_to_graph(stub=stub, graph=graph, device_name='SL Network Renderer')

    # get_input_program_list
    gdp_in = SLGraphDeviceProto(graph=graph, device=added_input_device)
    in_prog_list: SLInputProgramListProto = stub.get_input_program_list(gdp_in)
    if not len(in_prog_list.list) > 0:
        print(f'❌ Не найдены input programs')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    input_program: SLInputProgramProto = in_prog_list.list[0]

    added_encoder = add_custom_encoder_to_program(stub=stub, graph=graph, input_program=input_program)
    connect_encoder_to_output(added_output_device=added_output_device, graph=graph, encoder=added_encoder, stub=stub)

    # ============================================ check graph structure ===============================
    exist_graph = helper_get_graph_by_name(stub=stub, name=new_graph_name)
    if not exist_graph:
        print(f'❌ Не создан граф {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    exist_input_sdi_device = helper_get_graph_input_device_by_configurator_info(stub=stub, graph=graph, configurator_info=configurator_info)
    if not exist_input_sdi_device:
        print(f'❌ Нет input device "{input_sdi_device.display_name}" у графа {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    exist_program = helper_get_input_program_first(stub=stub, graph=exist_graph, device=exist_input_sdi_device)
    if not exist_program:
        print(f'❌ Нет input program у input device "{input_sdi_device.display_name}" графа {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    exist_encoder = helper_get_encoder_from_program_first(stub=stub, graph=exist_graph, input_program=exist_program)
    if not exist_encoder:
        print(f'❌ Нет encoder у  графа {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    exist_output_program_from_encoder = helper_get_output_program_from_encoder_first(stub=stub, graph=exist_graph, encoder=exist_encoder)
    if not exist_output_program_from_encoder:
        print(f'❌ Нет exist_output_program_from_encoder у графа {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    exist_output_device = helper_get_graph_output_device_first(stub=stub, graph=exist_graph)
    if not exist_output_device:
        print(f'❌ Нет exist_output_device у графа {new_graph_name}')
        test_ok = False

    test_ok &= is_graph_running(graph=graph, stub=stub)
    if not test_ok:
        print(f'❌ Статус графа {new_graph_name} не равен "Running"')

    if not helper_delete_graph(stub=stub, graph=exist_graph):
        print(f'❌ Не удалось удалить граф {new_graph_name}')
        test_ok = False

    print_test_result(test_ok, inspect.currentframe().f_code.co_name)



def test_T6TC3_2(get_stub):
    """
    То же самое, что test_T6TC3, но граф не создаётся, а импортируется.
    Create graph + add input SDI device + encoder AVC + addOutput device + connect Input to Encoder + Encoder to Output and start
    Ждём, когда граф перейдёт в состояние Running
    """

    print(f'\nT6TC3_2:  IMPORT (not Create) graph (add input SDI device + encoder AVC + addOutput device + connect Input to Encoder + '
          f'Encoder to Output and start.')
    test_ok = True

    stub = get_stub

    board_name = 'FD788' if project_settings.mode == 'build_test_release' else 'FD722'
    f_jsonname = os.path.join(project_settings.graphs_dir, f'{board_name}', f'{board_name}_T6TC3.json')
    # f_jsonname = os.path.join(project_settings.graphs_dir, 'FD788', 'FD788_T6TC3.json')

    jdata = helper_read_dict_from_json(f_jsonname=f_jsonname)
    new_graph_name = jdata['name'] + '_2'

    if not helper_delete_graph_by_name(stub=stub, graph_name=new_graph_name):
        print(f'❌ Не удалось удалить граф {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    graph, stopped = helper_import_graph(stub=stub, filename=f_jsonname, graph_name=new_graph_name)
    # if not helper_wait_graph_state(stub=stub, name=graph.name, state='sl_graph_stoped'):
    if not stopped:
        print(f'❌ Не удалось остановить граф {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    in_device_conf_info = jdata['input_devices'][0]['configurator_info']
    configurator_info = SLConfiguratorInfoProto(class_name=in_device_conf_info['class_name'], dll_name=in_device_conf_info['dll_name'])
    input_sdi_device_display_name = jdata['input_devices'][0]['display_name']

    # ============================================ check graph structure ===============================
    exist_graph: SLGraphProto = helper_get_graph_by_name(stub=stub, name=new_graph_name)
    if not exist_graph:
        print(f'❌ Не создан граф {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    exist_input_sdi_device = helper_get_graph_input_device_by_configurator_info(stub=stub, graph=exist_graph, configurator_info=configurator_info)
    if not exist_input_sdi_device:
        print(f'❌ Нет input device "{in_device_conf_info}" у графа {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    exist_program = helper_get_input_program_first(stub=stub, graph=exist_graph, device=exist_input_sdi_device)
    if not exist_program:
        print(f'❌ Нет input program у input device "{input_sdi_device_display_name}" графа {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    exist_encoder = helper_get_encoder_from_program_first(stub=stub, graph=exist_graph, input_program=exist_program)
    if not exist_encoder:
        print(f'❌ Нет encoder у  графа {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    exist_output_program_from_encoder = helper_get_output_program_from_encoder_first(stub=stub, graph=exist_graph, encoder=exist_encoder)
    if not exist_output_program_from_encoder:
        print(f'❌ Нет exist_output_program_from_encoder у графа {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    exist_output_device = helper_get_graph_output_device_first(stub=stub, graph=exist_graph)
    if not exist_output_device:
        print(f'❌ Нет exist_output_device у графа {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    test_ok &= is_graph_running(graph=graph, stub=stub)
    if not test_ok:
        print(f'❌ Статус графа {new_graph_name} не равен "Running"')

    if not helper_delete_graph_by_name(stub=stub, graph_name=new_graph_name):
        print(f'❌ Не удалось удалить граф {new_graph_name}')
        test_ok = False
    print_test_result(test_ok, inspect.currentframe().f_code.co_name)


def test_T6TC3_3(get_stub):
    """
    То же самое, что test_T6TC3, но граф не создаётся, а импортируется.
    Затем проверяется, что граф стартовал (перейдёт в состояние Running).
    Затем граф останавливается, экспортируется, полученный JSON сравнивается с исходным.
    """

    print(f'\nT6TC3_3:  import graph, export graph, compare JSON files')
    test_ok = True
    stub = get_stub

    board_name = 'FD788' if project_settings.mode == 'build_test_release' else 'FD722'
    f_jsonname = os.path.join(project_settings.graphs_dir, f'{board_name}', f'{board_name}_T6TC3.json')
    # f_jsonname = os.path.join(project_settings.graphs_dir, 'FD788', 'FD_T6TC3.json')

    jdata = helper_read_dict_from_json(f_jsonname=f_jsonname)
    new_graph_name = jdata['name'] + '_3'

    if not helper_delete_graph_by_name(stub=stub, graph_name=new_graph_name):
        print(f'❌ Не удалось удалить граф {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    graph, stopped = helper_import_graph(stub=stub, filename=f_jsonname, graph_name=new_graph_name)
    # if not helper_wait_graph_state(stub=stub, name=graph.name, state='sl_graph_stoped'):
    if not stopped:
        print(f'❌ Не удалось остановить граф {new_graph_name}')
        print_test_result(False, inspect.currentframe().f_code.co_name)
        return

    test_ok &= is_graph_running(graph=graph, stub=stub)
    if not test_ok:
        print(f'❌ Статус графа {new_graph_name} не равен "Running"')

    ex_graph: SLGraphStringProto = stub.export_graph(graph)
    jdata_out = json.loads(ex_graph.text)

    diff = DeepDiff(jdata, jdata_out)
    lst_diff = analyze_deep_diff(diff=diff)
    if lst_diff:
        print(lst_diff)
        test_ok = False

    if not helper_delete_graph(stub=stub, graph=graph):
        print(f'❌ Не удалось удалить граф {new_graph_name}')
    print_test_result(test_ok, inspect.currentframe().f_code.co_name)



def test_set_board_io_config_T6TC4(get_stub_board):
    """ set_board_io_config - на плате FD788 поменять входы/выходы IIIIOOOO -> OOOOIIII и обратно
    Для выполнения теста в исполняемом файле run_tests_sedunov_branch.sh проброшен device sys-forward командой:

    sudo lxc config device add pytestsedunovbranch sys-forward disk source=/sys/class/forward/fd788-${BOARD_NUMBER}
    path=/mnt/forward/fd788-${BOARD_NUMBER}

    В коде автотеста редактируется конфигурационный файл io_config (метод bash_edit_io_config), затем выполняется stub_board.set_board_io_config

    P.S. Если менять IO портов, то отваливаются девайсы от этих портов
    """
    board_number = 80739

    test_ok = True
    stub_board = get_stub_board
    boardinfo = stub_board.get_available_boards(SLEmptyProto()).list[0]
    board = boardinfo.board
    print('\n')

    if board.name != 'FD788':
        pytest.skip('Тест только для платы FD788')
        return

    # поменять первый раз
    # param = 'OOOOIIII'
    param = 'IIIOOOOI'
    bash_edit_io_config(board_number=board_number, param=param)
    result = set_board_io_config_directions(stub_board=stub_board, board=board, pins=boardinfo.io_config.pins, param=param)
    if not result == param:
        test_ok = False
        print(f'{Fore.RED}❌ Значения pins.directions "{result}" не сменились на ожидаемые "{param}"{Fore.RESET}')
    else:
        print(f'{Fore.GREEN}✅ {result=}{Fore.RESET}')

    # вернуть как было
    param = 'IIIIOOOO'
    bash_edit_io_config(board_number=board_number, param=param)
    result = set_board_io_config_directions(stub_board=stub_board, board=board, pins=boardinfo.io_config.pins, param=param)
    if not result == param:
        test_ok = False
        print(f'{Fore.RED}❌ Значения pins.directions "{result}" не сменились на ожидаемые "{param}"{Fore.RESET}')
    else:
        print(f'{Fore.GREEN}✅ {result=}{Fore.RESET}')

    print_test_result(test_ok, inspect.currentframe().f_code.co_name)


def test_set_board_genlock_T6TC5(get_stub_board):
    """ set_board_genlock - на плате поменять Genlock и обратно """
    print(f'\nT6TC5:   set_board_genlock - на плате поменять Genlock и обратно')
    test_ok = True
    stub_board = get_stub_board
    boardinfo = stub_board.get_available_boards(SLEmptyProto()).list[0]
    board = boardinfo.board

    for i in (0, 1, 2, 3, 4, 5, 0):
        genlock = SLGenlock(genlock=i, state_genlock=SLGenlockState.Value('SYNC_GENLOCK_LOCKING'), phase=3)
        result: SLGenlock = stub_board.set_board_genlock(SLBoardGenlock(board=board, genlock=genlock))
        sleep(1)
        zboardinfo: SLBoards = stub_board.get_available_boards(SLEmptyProto())
        boardinfo = zboardinfo.list[0]
        if result.genlock != boardinfo.genlock.genlock:
            test_ok = False
            print(f'❌ Неверно установлен genlock ({boardinfo.genlock.genlock}) - должно быть {i}')

    print_test_result(test_ok, inspect.currentframe().f_code.co_name)

    # [('SYNC_GENLOCK_MASTER', 0),
    #  ('SYNC_GENLOCK_NO_INPUT_SIGNAL', 1),
    #  ('SYNC_GENLOCK_LOCKING', 2),
    #  ('SYNC_GENLOCK_LOCKED', 3),
    #  ('SYNC_GENLOCK_HOLDOVER', 4),
    #  ('SYNC_UNKNOWN', 5)]

    # genlock = 0   boardinfo.genlock=пусто                          Genlock state=Master (No genlock)
    # genlock = 1   boardinfo.genlock=SYNC_GENLOCK_NO_INPUT_SIGNAL   Genlock state=No input signal (Genlock enabled, but no signal present)
    # genlock = 2   boardinfo.genlock=SYNC_GENLOCK_LOCKING           Genlock state=Locked (output is genlocked)
    # genlock = 3   boardinfo.genlock=SYNC_GENLOCK_NO_INPUT_SIGNAL   Genlock state=No input signal (Genlock enabled, but no signal present)
    # genlock = 4   boardinfo.genlock=SYNC_GENLOCK_NO_INPUT_SIGNAL   Genlock state=No input signal (Genlock enabled, but no signal present)
    # genlock = 5   boardinfo.genlock=SYNC_GENLOCK_NO_INPUT_SIGNAL   Genlock state=No input signal (Genlock enabled, but no signal present)

    # genlock = 6   boardinfo.genlock=SYNC_GENLOCK_NO_INPUT_SIGNAL   Genlock state=No input signal (Genlock enabled, but no signal present)
    # genlock = 9999   boardinfo.genlock=SYNC_GENLOCK_NO_INPUT_SIGNAL   Genlock state=No input signal (Genlock enabled, but no signal present)


def test_set_board_phase_T6TC6(get_stub_board):
    """ set_board_phase - на плате поменять phase и обратно """
    print(f'\nT6TC6:   set_board_phase - на плате поменять phase и обратно')
    test_ok = True
    stub_board = get_stub_board
    boardinfo = stub_board.get_available_boards(SLEmptyProto()).list[0]
    board = boardinfo.board

    for i in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 999, 0):
        genlock = SLGenlock(genlock=0, state_genlock=SLGenlockState.Value('SYNC_UNKNOWN'), phase=i)
        result: SLGenlock = stub_board.set_board_phase(SLBoardGenlock(board=board, genlock=genlock))
        sleep(0.2)
        zboardinfo: SLBoards = stub_board.get_available_boards(SLEmptyProto())
        boardinfo = zboardinfo.list[0]
        if i != boardinfo.genlock.phase:
            test_ok = False
            print(f'❌ Неверно установлена phase ({boardinfo.genlock.phase}) - должно быть {i}')

    print_test_result(test_ok, inspect.currentframe().f_code.co_name)

# =================================================================================================================================================

# Этот тест не нужен, т.к. поменять mode нельзя
# E           grpc._channel._InactiveRpcError: <_InactiveRpcError of RPC that terminated with:
# E               status = StatusCode.CANCELLED
# E               details = "Can't set the mode, the device is busy probably. Please close all graphs and try again!"
# E               debug_error_string = "UNKNOWN:Error received from peer  {grpc_status:1, grpc_message:"Can\'t set the mode, the device is busy " +
#                                      "probably. Please close all graphs and try again!"}"
# E           >
# def test_set_board_mode_T6TC7(get_stub_board):
#     """ set_board_mode - на плате поменять mode и обратно """
#     # 'v4l2,alsa'
#     test_ok = True
#     stub_board = get_stub_board
#     boardinfo = stub_board.get_available_boards(SLEmptyProto()).list[0]
#     board = boardinfo.board
#
#     for i in ('s', '0', '1', '23', 'dddddddddddddddddddd dddddddddddddddddd', 'v4l2,alsa'):
#         mode = SLModeProto(mode=i, available=['aaa', 'rrrr'])
#         result: SLModeProto = stub_board.set_board_mode(SLBoardModeProto(board=board, mode=mode))
#         sleep(0.2)
#         zboardinfo: SLBoards = stub_board.get_available_boards(SLEmptyProto())
#         boardinfo = zboardinfo.list[0]
#         if i != boardinfo.mode:
#             test_ok = False
#             print(f'❌ Неверно установлена mode ({boardinfo.mode}) - должно быть "{i}"')
#
#     print_test_result(test_ok, inspect.currentframe().f_code.co_name)



def is_graph_running(stub=None, graph=None):
    ok = helper_start_graph(stub=stub, graph=graph, attempts=2)
    return ok


def connect_encoder_to_output(added_output_device=None, graph=None, encoder=None, stub=None):
    gedp = SLGraphEncoderDeviceProto(graph=graph, encoder=encoder, device=added_output_device)
    new_o_p: SLOutputProgramProto = stub.add_device_to_encoder(gedp)
    new_o_p.name = '63'
    new_o_p.number = 63
    new_o_p.provider_name = '63'
    gop = SLGraphOutputProgramProto(graph=graph, output_program=new_o_p)
    stub.set_output_program_settings(gop)


def add_custom_input_device_to_graph(stub=None, graph=None, input_sdi_device=None):
    # add_input_device_to_graph
    jstr = json.loads(input_sdi_device.settings)
    for i, x in enumerate(jstr[0]['params']):
        if x['desc'] == 'Number of audio lines':
            jstr[0]['params'][i]['value'] = '1'
    settings2 = json.dumps(jstr)
    input_sdi_device2 = SLDeviceProto(display_name=input_sdi_device.display_name,
                                      type=input_sdi_device.type,
                                      ll_device_info=input_sdi_device.ll_device_info,
                                      settings=settings2,
                                      configurator_info=input_sdi_device.configurator_info,
                                      guid=input_sdi_device.guid
                                      )
    gdp_in = SLGraphDeviceProto(graph=graph, device=input_sdi_device2)
    added_input_device: SLDeviceProto = stub.add_input_device_to_graph(gdp_in)
    return added_input_device


def add_custom_encoder_to_program(stub=None, graph=None, input_program=None):
    encoder_support: SLEncoderSupportProto = stub.get_encoder_support(SLEmptyProto())
    audio = encoder_support.audio[0]
    video = encoder_support.video[0]
    new_settings_encoder = json.dumps([json.loads(video.settings)[0], json.loads(audio.settings)[0]])
    stream_audio = SLStreamProto(out_stream_pid=0, stream_id=0, stream_pid=700, type=SLStreamTypeProto.audio_stream)
    stream_video = SLStreamProto(out_stream_pid=0, stream_id=0, stream_pid=500, type=SLStreamTypeProto.video_stream)
    stream_scte = SLStreamProto(out_stream_pid=0, stream_id=0, stream_pid=1200, type=SLStreamTypeProto.scte104_stream)
    stream_teletext = SLStreamProto(out_stream_pid=0, stream_id=0, stream_pid=1100, type=SLStreamTypeProto.teletext_stream)
    encoder = SLEncoderProto(name='encoder_name', video=SLVideoEncoderTypeProto.sl_mc_avc_encoder,
                             audio=SLAudioEncoderTypeProto.sl_mc_mpeg1_encoder, settings=new_settings_encoder,
                             streams=[stream_video, stream_teletext, stream_scte, stream_audio])
    helper_stop_graph(stub=stub, graph=graph)
    gpep = SLGraphProgramEncoderProto(graph=graph, input_program=input_program, encoder=encoder)
    added_encoder: SLEncoderProto = stub.add_encoder_to_program(gpep)
    return added_encoder


def set_board_io_config_directions(stub_board=None, board=None, pins=None, param=''):
    for i, v in enumerate(param):
        pins[i].direction = SLPinDirection.Value('DIR_OUTPUT') if v == 'O' else SLPinDirection.Value('DIR_INPUT')

    slioconfig: SLIOConfig = stub_board.set_board_io_config(SLBoardIOConfig(board=board, pins=pins))
    result = ''.join(['O' if x.direction != 0 else 'I' for x in slioconfig.pins])
    return result


def bash_edit_io_config(board_number=0, param=''):
    subprocess.run(['sudo', 'sh', '-c', f'echo {param} > /mnt/forward/fd788-{board_number}/io_config'], capture_output=True, text=True)


def test_genlock_T6TC999(get_stub_board):
    stub_board = get_stub_board
    boardinfo = stub_board.get_available_boards(SLEmptyProto()).list[0]
    board = boardinfo.board

    t = (0, 0, 0)
    print(t)

    genlock = SLGenlock(genlock=0, state_genlock=0, phase=33)
    result: SLGenlock = stub_board.set_board_genlock(SLBoardGenlock(board=board, genlock=genlock))

    for i in range(1, 101):
        x = print(i, end=' ') if i % 10 == 0 else None
        zboardinfo: SLBoards = stub_board.get_available_boards(SLEmptyProto())
        g = zboardinfo.list[0].genlock
        t2 = (g.genlock, g.state_genlock, g.phase)
        if t2 != t:
            t = t2
            print(t2)
