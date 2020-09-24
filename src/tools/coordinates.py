"""Tools for performing vector and coordinate conversions."""

import math

_CONV = 180.0/math.pi

def sphericalToCartesian(magnitude, azimuthal, polar):
    """Convert a vector from spherical to Cartesian coordinates.
    
    Parameters
    ----------
    magnitude : float
        The magnitude of the vector.
    azimuthal : float
        The angle in degrees of the vector, measured downward from the positive
        z-axis.
    polar : float
        The angle in degrees of the vector, measured counter-clockwise from
        the positive x-axis.
    
    Returns
    -------
    float
        The x-coordinate of the vector.
    float
        The y-coordinate of the vector.
    float
        THe z-coordinate of the vector.
    """
    azimuthal = azimuthal*math.pi/180.0
    polar = polar*math.pi/180.0
    xval = magnitude * math.sin(azimuthal) * math.cos(polar)
    yval = magnitude * math.sin(azimuthal) * math.sin(polar)
    zval = magnitude * math.cos(azimuthal)
    return [xval, yval, zval]
    
def cartesianToSpherical(xComp, yComp, zComp, negateMagnitude=False, 
                         tolerance=1E-10):
    """Convert a vector from Cartesian to spherical coordinates.
    
    Parameters
    ----------
    xComp : float
        The x-component of the vector.
    yComp : float
        The y-component of the vector.
    zComp : float
        The z-component of the vector.
    negateMagnitude : bool
        Whether to prefer a negative value of the magnitude, accounting for
        the reversed direction by adding 180 degrees to the azimuthal angle.
    tolerance : float
        How maximum absolute value a number may have and still be treated as
        zero.
    
    Returns
    -------
    float
        The magnitude of the vector.
    float
        The azimuthal angle in degrees.
    float
        The polar angle in degrees.
    """
    ans = None
    mag = math.sqrt(xComp*xComp + yComp*yComp + zComp*zComp)
    if mag < tolerance:
        ans = [0.0, 0.0, 0.0]

    proj2 = xComp*xComp + yComp*yComp
    if ans is None and proj2 < tolerance:
        ans = [mag, 0.0, 0.0]
    elif abs(zComp) < tolerance:
        if abs(xComp) < tolerance:
            ans = [mag, 90.0, 90.0]
        if abs(yComp) < tolerance:
            ans = [mag, 90.0, 0.0]
        else:
            ans = [mag, 90.0, math.acos(xComp/mag)*_CONV]
    else:
        azimuth = math.acos(zComp/mag)
        ans = [mag, azimuth*_CONV, 
               math.acos(xComp/(mag*math.sin(azimuth)))*_CONV]
    
    if negateMagnitude:
        ans = [-1*ans[0], 180+ans[1], ans[2]]
    return ans

def equalEnough(numA, numB, tol=0.000001):
    """Return whether two numbers are close enough to be considered equal."""
    return math.fabs(numA - numB) <= tol

def clean(point):
    """Return a float with digits farther out than fifth place truncated."""
    tmp = []
    for pts in point:
        tmp.append(float('%.5f' % pts))
    return (tmp[0], tmp[1], tmp[2])

