"""Classes to monitor stability in some value."""

from time import time

from src.tools.general import simpleLinearRegression

class StabilityTrend(object):
    """A class for tracking stability based on trend.
    
    Parameters
    ----------
    bufferSize : int
        The number of data points of which to keep track.
    tolerance : float
        The maximum deviation from zero which the slope can have while still
        being considered stable.
    timeout : float
        The maximum amount of time to monitor the system.
    """
    def __init__(self, bufferSize, tolerance, timeout=None):
        self._bufferSize = bufferSize
        self._maxAllowed = abs(tolerance)
        self._minAllowed = -1.0 * abs(tolerance)
        if timeout is None:
            self._timeout = float('inf')
        else:
            self._timeout = timeout

        self._times = []
        self._values = []
        self._length = 0

        self._max = None
        self._min = None
        self._slope = None

        self._startTime = time()

    def addPoint(self, value):
        """Add a point to the monitor.
        
        Parameters
        ----------
        value : float
            The value to add to the monitor.
        """
        newTime = time()
        self._times.append(newTime)
        self._values.append(value)
        if self._length + 1 > self._bufferSize:
            self._times.pop(0)
            self._values.pop(0)
        else:
            self._length += 1
        stats = simpleLinearRegression(self._times, self._values)
        self._slope = stats[0]
        self._min = stats[3]
        self._max = stats[4]

    def isStable(self):
        """Return whether the system is stable.
        
        Returns
        -------
        bool
            Whether the system is stable.
        """
        return self._minAllowed < self._slope < self._maxAllowed

    def isTimedOut(self):
        """Return whether the monitor has timed out.
        
        Returns
        -------
        bool
            Whether the system has passed the timeout.
        """
        return time() - self._startTime > self._timeout

    def isBufferFull(self):
        """Return whether the buffer is full.
        
        Returns
        -------
        bool
            Whether the monitor's buffer has been filled.
        """
        return self._length >= self._bufferSize

    def isFinished(self):
        """Return whether the wait for stability can end.
        
        Returns
        -------
        bool
            Whether the software can proceed, meaning either that the buffer
            is full and the system is stable or that the monitor has timed out.
        """
        return (self.isBufferFull() and self.isStable()) or self.isTimedOut()

    def getTrend(self):
        """Return the slope of the line formed by the data.
        
        Returns
        -------
        float
            The slope of the line formed by the data.
        """
        return self._slope


class StabilitySetpoint(object):
    """A class for tracking stability based on proximity to a setpoint.
    
    Parameters
    ----------
    bufferSize : int
        The number of data points of which to keep track.
    setpoint : float
        The desired value for the system values.
    tolerance : float
        The maximum deviation from zero which the slope can have while still
        being considered stable.
    timeout : float
        The maximum amount of time to monitor the system.
    """
    def __init__(self, bufferSize, setpoint, tolerance, timeout=None):
        self._bufferSize = bufferSize
        self._maxAllowed = setpoint + abs(tolerance)
        self._minAllowed = setpoint - abs(tolerance)
        if timeout is None:
            self._timeout = float('inf')
        else:
            self._timeout = timeout

        self._times = []
        self._values = []
        self._length = 0

        self._max = None
        self._min = None
        self._slope = None

        self._startTime = time()

    def addPoint(self, value):
        """Add a point to the monitor.
        
        Parameters
        ----------
        value : float
            The value to add to the monitor.
        """
        newTime = time()
        self._times.append(newTime)
        self._values.append(value)
        if self._length + 1 > self._bufferSize:
            self._times.pop(0)
            self._values.pop(0)
        else:
            self._length += 1
        stats = simpleLinearRegression(self._times, self._values)
        self._slope = stats[0]
        self._min = stats[3]
        self._max = stats[4]

    def isStable(self):
        """Return whether the system is stable.
        
        Returns
        -------
        bool
            Whether the system is stable.
        """
        return self._minAllowed < self._min < self._max < self._maxAllowed

    def isTimedOut(self):
        """Return whether the monitor has timed out.
        
        Returns
        -------
        bool
            Whether the system has passed the timeout.
        """
        return time() - self._startTime > self._timeout

    def isBufferFull(self):
        """Return whether the buffer is full.
        
        Returns
        -------
        bool
            Whether the monitor's buffer has been filled.
        """
        return self._length >= self._bufferSize

    def isFinished(self):
        """Return whether the wait for stability can end.
        
        Returns
        -------
        bool
            Whether the software can proceed, meaning either that the buffer
            is full and the system is stable or that the monitor has timed out.
        """
        return (self.isBufferFull() and self.isStable()) or self.isTimedOut()

    def getTrend(self):
        """Return the slope of the line formed by the data.
        
        Returns
        -------
        float
            The slope of the line formed by the data.
        """
        return self._slope


class StabilityTimer(object):
    """A timer for checking for stability.
    
    Parameters
    ----------
    duration : float
        The time in seconds over which the values should be stable before
        the timer asserts that it is finished.
    stability : float
        The largest separation between the maximum and minimum known values
        for which the timer may consider itself to be stable.
    timeout : float
        The maximum time in seconds to wait for the values to become 
        stable.
    """

    def __init__(self, duration, stability, timeout=None):
        self._duration = duration
        self._stability = stability
        self._timeout = timeout

        self._times = []
        self._values = []
        self._startTime = time()

        self._max = float('inf')
        self._min = float('-inf')

    def addValue(self, newValue):
        """Associate a new value with the timer.
        
        Parameters
        ----------
        newValue : float
            The value to add to the timer.
        """
        self._times.append(time())
        self._values.append(newValue)
        if len(self._values) == 0:
            self._max = newValue
            self._min = newValue
        elif newValue > self._max:
            self._max = newValue
        elif newValue < self._min:
            self._min = newValue
        if not self.isStable():
            self._times = [self._times[-1]]
            self._values = [self._values[-1]]
            self._max = newValue
            self._min = newValue

    def isStable(self):
        """Return whether the values are stable.
        
        Returns
        -------
        bool
            Whether the values associated with the specified timer are
            close enough to be considered stable.
        """
        return self._max - self._min < self._stability

    def getStableTime(self):
        """Return how long the timer has been stable.
        
        Returns
        -------
        float
            How long the values associated with the timer have been
            close enough to be considered stable. If the values are
            *not* stable, return -1.
        """
        try:
            return self._times[-1] - self._times[0]
        except IndexError:
            return -1

    def isTimeoutElapsed(self):
        """Return whether the timer has timed out.
        
        Returns
        -------
        bool
            Whether the timer has timed out.
        """
        if self._timeout is None:
            return False
        try:
            return self._times[-1] - self._startTime >= self._timeout
        except IndexError:
            return False

    def isFinished(self):
        """Return whether the desired conditions have been met.
        
        Returns
        -------
        bool
            Whether the desired conditions have been met. Return `True`
            if either the timeout has elapsed or the value has remained
            stable for the specified length of time. Otherwise, return
            `False`.
        """
        return self.getStableTime() >= self._duration or self.isTimeoutElapsed()

    def getStats(self):
        """Return the maximum and minimum values and the slope of the line.
        
        Note that whenever a new value is added to the timer, if the new
        value is outside the stability range defined by previous values, the
        arrays are cleared and the maximum and minimum values are both set to
        the newly added value.
        
        Returns
        -------
        float
            The maximum known value.
        float
            The minimum known value.
        float
            The slope of the line formed by the known values and the times
            at which the respective values were added, in units/s.
        """
        slope = simpleLinearRegression(self._times, self._values)[0]
        return (self._max, self._min, slope)

class BufferedStabilityTimer(object):
    """A timer for checking for stability, which keeps only new points.
    
    Parameters
    ----------
    stability : float
        The largest separation between the maximum and minimum known values
        for which the timer may consider itself to be stable.
    bufferSize : int
        The maximum number of points to keep at any given time.
    timeout : float
        The maximum time in seconds to wait for the values to become 
        stable.
    """

    def __init__(self, stability, bufferSize, timeout=None):
        self._stability = stability
        self._bufferSize = bufferSize
        self._timeout = timeout

        self._times = []
        self._values = []
        self._startTime = time()

    def addValue(self, newValue):
        """Associate a new value with the timer.
        
        Parameters
        ----------
        newValue : float
            The value to add to the timer.
        """
        self._times.append(time())
        self._values.append(newValue)
        if len(self._times) > self._bufferSize:
            self._times.pop(0)
            self._values.pop(0)

    def isBufferFull(self):
        """Return whether the buffer is full.
        
        Returns
        -------
        bool
            Whether the buffer is full.
        """
        return len(self._times) == self._bufferSize

    def isStable(self):
        """Return whether the values are stable.
        
        Returns
        -------
        bool
            Whether the values associated with the specified timer are
            close enough to be considered stable.
        """
        return max(self._values) - min(self._values) < self._stability

    def isTimeoutElapsed(self):
        """Return whether the timer has timed out.
        
        Returns
        -------
        bool
            Whether the timer has timed out.
        """
        if self._timeout is None:
            return False
        try:
            return self._times[-1] - self._startTime >= self._timeout
        except IndexError:
            return False

    def isFinished(self):
        """Return whether the desired conditions have been met.
        
        Returns
        -------
        bool
            Whether the desired conditions have been met. Return `True`
            if either the timeout has elapsed or the value has remained
            stable for the specified length of time. Otherwise, return
            `False`.
        """
        return self.isBufferFull() or self.isTimeoutElapsed()

    def getStats(self):
        """Return the maximum and minimum values and the slope of the line.
        
        Note that whenever a new value is added to the timer, if the new
        value is outside the stability range defined by previous values, the
        arrays are cleared and the maximum and minimum values are both set to
        the newly added value.
        
        Returns
        -------
        float
            The maximum known value.
        float
            The minimum known value.
        float
            The slope of the line formed by the known values and the times
            at which the respective values were added, in units/s.
        """
        slope = simpleLinearRegression(self._times, self._values)[0]
        return (max(self._values), min(self._values), slope)
