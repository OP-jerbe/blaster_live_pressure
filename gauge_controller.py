"""This module contains drivers for the following equipment from Pfeiffer
Vacuum:

* TPG 262 and TPG 261 Dual Gauge. Dual-Channel Measurement and Control
    Unit for Compact Gauges
"""

import math
import random
import time

import serial

# Code translations constants
MEASUREMENT_STATUS = {
    0: 'Measurement data okay',
    1: 'Underrange',
    2: 'Overrange',
    3: 'Sensor error',
    4: 'Sensor off (IKR, PKR, IMR, PBR)',
    5: 'No sensor (output: 5,2.0000E-2 [mbar])',
    6: 'Identification error',
}
GAUGE_IDS = {
    'TPR': 'Pirani Gauge or Pirani Capacitive gauge',
    'IKR9': 'Cold Cathode Gauge 10E-9 ',
    'IKR11': 'Cold Cathode Gauge 10E-11 ',
    'PKR': 'FullRange CC Gauge',
    'PBR': 'FullRange BA Gauge',
    'IMR': 'Pirani / High Pressure Gauge',
    'CMR': 'Linear gauge',
    'noSEn': 'no SEnsor',
    'noid': 'no identifier',
}
PRESSURE_UNITS = {0: 'mbar', 1: 'Torr', 2: 'Pascal'}


class GaugeControllerx(object):
    r"""Abstract class that implements the common driver for the Pfeiffer TPG26x and AGC-100
    dual channel measurement and control unit. The driver implements
    the following 6 commands out the 39 in the specification:

    * PNR: Program number (firmware version)
    * PR[1,2]: Pressure measurement (measurement data) gauge [1, 2]
    * PRX: Pressure measurement (measurement data) gauge 1 and 2
    * TID: Transmitter identification (gauge identification)
    * UNI: Pressure unit
    * RST: RS232 test

    This class also contains the following class variables, for the specific
    characters that are used in the communication:

    :var ETX: End text (Ctrl-c), chr(3), \\x15
    :var CR: Carriage return, chr(13), \\r
    :var LF: Line feed, chr(10), \\n
    :var ENQ: Enquiry, chr(5), \\x05
    :var ACK: Acknowledge, chr(6), \\x06
    :var NAK: Negative acknowledge, chr(21), \\x15
    """

    ETX = chr(3)  # \x03
    CR = chr(13)  # \r
    LF = chr(10)  # \n
    ENQ = chr(5)  # \x05
    ACK = chr(6)  # \x06
    NAK = chr(21)  # \x15

    def __init__(self, port='/dev/ttyUSB0', baudrate=9600) -> None:
        """Initialize internal variables and serial connection

        :param port: The COM port to open. See the documentation for
            `pyserial <http://pyserial.sourceforge.net/>`_ for an explanation
            of the possible value. The default value is '/dev/ttyUSB0'.
        :type port: str or int
        :param baudrate: 9600, 19200, 38400 where 9600 is the default
        :type baudrate: int
        """
        # The serial connection should be setup with the following parameters:
        # 1 start bit, 8 data bits, No parity bit, 1 stop bit, no hardware
        # handshake. These are all default for Serial and therefore not input
        # below
        self.serial = serial.Serial(port=port, baudrate=baudrate, timeout=1)

    def _cr_lf(self, string) -> str:
        """Pad carriage return and line feed to a string

        :param string: String to pad
        :type string: str
        :returns: the padded string
        :rtype: str
        """
        return string + self.CR + self.LF  # return '{string}\r\n'

    def _send_command(self, command) -> None:
        """Send a command and check if it is positively acknowledged

        :param command: The command to send
        :type command: str
        :raises IOError: if the negative acknowledged or a unknown response
            is returned
        """
        self.serial.write(
            bytes(self._cr_lf(command), 'utf-8')
        )  # serial.write(b'{command}\r\n')
        response = self.serial.readline().decode()
        if response == self._cr_lf(self.NAK):  # if response == '\x15\r\n'
            message = 'Serial communication returned negative acknowledge'
            raise IOError(message)
        elif response != self._cr_lf(self.ACK):  # if response != '\x06\r\n'
            message = 'Serial communication returned unknown response:\n{}'.format(
                repr(response)
            )
            raise IOError(message)

    def _get_data(self) -> str:
        """Get the data that is ready on the device

        :returns: the raw data
        :rtype:str
        """
        self.serial.write(bytes(self.ENQ, 'utf-8'))  # serial.write(b'\x05')
        data = self.serial.readline().decode()
        return data.rstrip(self.LF).rstrip(self.CR)

    def _clear_output_buffer(self) -> str:
        """Clear the output buffer"""
        time.sleep(0.1)
        just_read = 'start value'
        out = ''
        while just_read != '':
            just_read = self.serial.read().decode()
            out += just_read
        return out

    def program_number(self) -> str:
        """Return the firmware version

        :returns: the firmware version
        :rtype: str
        """
        self._send_command('PNR')  # serial.write(b'PNR\r\n')
        return self._get_data()

    def pressure_gauge(self, gauge=1) -> tuple[float, tuple[int, str]]:
        """Return the pressure measured by gauge X

        :param gauge: The gauge number, 1 or 2
        :type gauge: int
        :raises ValueError: if gauge is not 1 or 2
        :return: (value, (status_code, status_message))
        :rtype: tuple
        """
        if gauge not in [1, 2]:
            message = 'The input gauge number can only be 1 or 2'
            raise ValueError(message)
        self._send_command(
            'PR' + str(gauge)
        )  # serial.write(b'PR1\r\n') OR serial.write(b'PR2\r\n')
        reply = self._get_data()
        status_code = int(reply.split(',')[0])
        value = float(reply.split(',')[1])
        return value, (status_code, MEASUREMENT_STATUS[status_code])

    def pressure_gauges(self) -> tuple[float, tuple[int, str], float, tuple[int, str]]:
        """Return the pressures measured by the gauges

        :return: (value1, (status_code1, status_message1), value2,
            (status_code2, status_message2))
        :rtype: tuple
        """
        self._send_command('PRX')  # serial.write(b'PRX\r\n')
        reply = self._get_data()
        # The reply is on the form: x,sx.xxxxEsxx,y,sy.yyyyEsyy
        status_code1 = int(reply.split(',')[0])
        value1 = float(reply.split(',')[1])
        status_code2 = int(reply.split(',')[2])
        value2 = float(reply.split(',')[3])
        return (
            value1,
            (status_code1, MEASUREMENT_STATUS[status_code1]),
            value2,
            (status_code2, MEASUREMENT_STATUS[status_code2]),
        )

    def gauge_identification(self) -> tuple[str, str, str, str]:
        """Return the gauge identication

        :return: (id_code_1, id_1, id_code_2, id_2)
        :rtype: tuple
        """
        self._send_command('TID')  # serial.write(b'TID\r\n')
        reply = self._get_data()
        id1, id2 = reply.split(',')
        return id1, GAUGE_IDS[id1], id2, GAUGE_IDS[id2]

    def pressure_unit(self) -> str:
        """Return the pressure unit

        :return: the pressure unit
        :rtype: str
        """
        self._send_command('UNI')  # serial.write(b'UNI\r\n')
        unit_code = int(self._get_data())
        return PRESSURE_UNITS[unit_code]

    def rs232_communication_test(self) -> bool:
        """RS232 communication test

        :return: the status of the communication test
        :rtype: bool
        """
        self._send_command('RST')  # serial.write(b'RST\r\n')
        self.serial.write(bytes(self.ENQ, 'utf-8'))  # serial.write(b'\x05')
        self._clear_output_buffer()
        test_string_out = ''
        for char in 'a1':
            self.serial.write(bytes(char, 'utf-8'))  # serial.write(b'a1')
            test_string_out += self._get_data().rstrip(self.ENQ)
        self._send_command(self.ETX)  # serial.write(b'\x03\r\n')
        return test_string_out == 'a1'

    def open_port(self) -> str:
        """Open the serial COM port

        :return: the status of the COM port
        :rtype: str
        """
        if self.serial.is_open is not True:
            self.serial.open()
        com_status = 'Serial port open'
        return com_status

    def close_port(self) -> str:
        """Close the serial COM port

        :return: the status of the COM port
        :rtype: str
        """
        if self.serial.is_open is True:
            self.serial.close()
        com_status = 'Serial port closed'
        return com_status


class GaugeController2(GaugeControllerx):
    """Driver for the Pfeiffer TPG262 and AGC-100 dual channel measurement and control unit"""

    def __init__(self, port='/dev/ttyUSB0', baudrate=9600) -> None:
        """Initialize internal variables and serial connection

        :param port: The COM port to open. See the documentation for
            `pyserial <http://pyserial.sourceforge.net/>`_ for an explanation
            of the possible value. The default value is '/dev/ttyUSB0'.
        :type port: str or int
        :param baudrate: 9600, 19200, 38400 where 9600 is the default
        :type baudrate: int
        """
        super(GaugeController2, self).__init__(port=port, baudrate=baudrate)


class GaugeController1(GaugeControllerx):
    """Driver for the Pfeiffer TPG261 and AGC-100 single channel measurement and control unit"""

    def __init__(self, port='/dev/ttyUSB0', baudrate=9600) -> None:
        """Initialize internal variables and serial connection

        :param port: The COM port to open. See the documentation for
            `pyserial <http://pyserial.sourceforge.net/>`_ for an explanation
            of the possible value. The default value is '/dev/ttyUSB0'.
        :type port: str or int
        :param baudrate: 9600, 19200, 38400 where 9600 is the default
        :type baudrate: int
        """
        super(GaugeController1, self).__init__(port=port, baudrate=baudrate)


class SimGaugeControllerx:
    """Mock version of the GaugeControllerx driver for testing without hardware."""

    def __init__(self, *args, **kwargs) -> None:
        self._open = True
        self._iteration = 0
        self._A = 1e-6  # Initial pressure
        self._k = 0.15  # Decay rate — tweak as needed
        self._noise_amplitude = 1e-9  # Small random fluctuation
        self._P_min = 5e-8  # Floor value for pressure

    def pressure_gauge(self, gauge=1) -> tuple[float, tuple[int, str]]:
        _decay = self._A * math.exp(-self._k * self._iteration)
        _noise = random.uniform(-self._noise_amplitude, self._noise_amplitude)
        value = round(self._P_min + _decay + _noise, 9)
        self._iteration += 1
        status_code = 0
        return value, (status_code, MEASUREMENT_STATUS[status_code])

    def pressure_gauges(self) -> tuple[float, tuple[int, str], float, tuple[int, str]]:
        return (
            round(random.uniform(1e-7, 2e-7), 9),
            (0, MEASUREMENT_STATUS[0]),
            round(random.uniform(1e-6, 2e-6), 8),
            (0, MEASUREMENT_STATUS[0]),
        )

    def gauge_identification(self) -> tuple[str, str, str, str]:
        return 'TPR', GAUGE_IDS['TPR'], 'IKR9', GAUGE_IDS['IKR9']

    def pressure_unit(self) -> str:
        return PRESSURE_UNITS[0]

    def rs232_communication_test(self) -> bool:
        return True

    def open_port(self) -> str:
        self._open = True
        message = 'Mock serial port open'
        print(message)
        return message

    def close_port(self) -> str:
        self._open = False
        message = 'Mock serial port closed'
        print(message)
        return message
