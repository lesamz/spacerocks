# SpaceRock

The primary data structure in `spacerocks` is a class called `SpaceRock`. 
_You can instantiate a `SpaceRock` object using any valid set of 6 Keplerian 
elements, or a state vector._

## Instantiation

```Python
from spacerocks import SpaceRock
from spacerocks.units import Units

units = Units()
units.timescale = 'utc'

rock = SpaceRock(a=44, 
                 e=0.1, 
                 inc=10, 
                 node=140, 
                 arg=109, 
                 M=98, 
                 H=7, 
                 epoch='1 December 2021', 
                 origin='ssb', 
                 frame='eclipJ2000', 
                 units=units)
```
The `Units` object we instantiated is extremely useful for avoiding bugs, 
as it allows for an explicit set of units to be specified only once. 
You can read more about it [here](./Units.md).

Note that you can also pass a JD or an MJD as an epoch. 
If you provide a string (in any format) the program will use `dateutil` 
to try to parse the date. This is slow when compared to passing explicit 
values and time formats.

You can then access the attributes of your `SpaceRock` object. 
The attributes are lazily computed in the interest of efficiency. 
The attributes all carry `astropy` units, with angles stored as `Angle` 
objects, distances stored as `Distance` objects, and times 
stored as `Time` objects. This ensures a complete lack of ambiguity, 
and facilitates unit conversions.

The attributes of a `SpaceRock` object are listed in the tables below.

| Orbital Parameter                      | Attribute    |
|:---------------------------------------|:-------------|
| semi-major axis                        | a            |
| eccentricity                           | e            |
| inclination                            | inc          |
| longitude of ascending node            | node         |
| longitude of pericenter                | varpi        |
| argument of pericenter                 | arg          |
| mean anomaly                           | M            |
| true anomaly                           | f            |
| eccentric anomaly                      | E            |
| semi-minor axis                        | b            |
| pericenter distance                    | q            |
| apocenter distance                     | Q            |


| Metadata                               | Attribute    |
|:---------------------------------------|:-------------|
| name                                   | name         |
| epoch                                  | epoch        |


| Physical Property                      | Attribute  | 
|:---------------------------------------|:-----------|
| absolute magnitude                     | H          |
| phase-slope constant                   | G          |
| albedo                                 | albedo     |
| mass                                   | mass       |
| radius                                 | radius     |
| diameter                               | diameter   |


## Vectorization

`SpaceRock` objects are vectorized, allowing for the processing of multiple objects at once. 

```Python
rocks = SpaceRock(a=[44, 45], 
                  e=[0.1, 1.2], 
                  inc=[10, 170], 
                  node=[140, 303], 
                  arg=[109, 23], 
                  f=[98, 124], 
                  H=[7, 8.2],
                  epoch=['1 December 2021', '3 December 2021'], 
                  origin='ssb', 
                  units=units)
```
Notice that a `SpaceRock` object can handle both elliptical and hyperbolic orbits 
simultaneously (though parabolic orbits are not yet supported), and it can handle 
nonuniform epochs. 

## Object Slicing

`SpaceRock` objects have a number of other utilities. 
First, you can slice `SpaceRock` objects in a Pythonic way
```Python
r = rocks[rocks.e < 1]
```

## Coordinate Transformations

You can easily change the origin of the coordinate system. This is particularly 
useful for converting the Minor Planet Center's heliocentric elements to 
barycentric elements. 
```Python
# convert to heliocentric coordinates
rocks.to_helio()

# convert back to barycentric coordinates
rocks.to_bary()

# convert to New Horizons-centric coordinates
rocks.change_origin(spiceid=-98)
```

You can also change the coordinate frame between `J2000` and `ecliptic J2000`.
```Python
# Convert to J2000 coordinates
rocks.change_frame('J2000')

# Convert back to ecliptic J2000 coordinates
rocks.change_frame('eclipJ2000')
```

## The `propagate` Method

You can use the `propagate` method to propagate the rocks to any epochs. 
This method uses `rebound's` `ias15` integrator under the hood, and automatically 
synchronizes the epochs of the rocks so you don't have to. Notice that we are 
specifying the epochs to be in Barycentric Dynamical Time.

```Python
units = Units()
units.timescale = 'tdb'

prop, planets, sim = rock.propagate(epochs=['2 December 2021', '4 December 2021'], model='PLANETS', units=units)
```

Here `prop` is a `SpaceRock` object containing the test particles at 
all of the epochs, `planets` is a `SpaceRock` object containing the 
perturbers at all of the epochs, and `sim` is the rebound simulation 
object at the final epoch. The `model` argument sets the perturbers as follows.

| model | Perturbers                                                                      |
|:-----|:--------------------------------------------------------------------------------|
|   `SUN`   | Sun                                                                             |
|   `GIANTS`   | Sun, Jupiter, Saturn, Uranus, Neptune                                           |
|   `PLANETS`   | Sun, Mercury, Venus, Earth, Moon, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto |
|   `HORIZONS`   | Full set of JPL Horizons perturbers                                             |

The perturbers' masses are from JPL Horizons, and their state vectors are computed using `spiceypy`.


## The `observe` Method

You can use the `observe` method compute objects' ephemerides from an 
arbitrary location in the solar system. Here we compute the ephemerides of
our rocks from DECam.

```Python
obs = rocks.observe(obscode='W84')
```

The only argument taken by `observe` is an `obscode` (see [this link](https://minorplanetcenter.net/iau/lists/ObsCodesF.html) for a full list) or a `spiceid` (`Earth`, `Jupiter Barycenter`, `-98`, etc.).

The `observe` method returns an `Ephemerides` object which contains the rocks' state 
vectors with respect to the observer in the equatorial frame, corrected for light travel time. 
These values allow us to compute the rocks' observable properties, which 
are accessible as attriutes to the [Ephemerides](./Ephemerides.md) object.

## The `to_file` Method

Finally, you can write and read `SpaceRock` objects to and from `asdf` files.
```Python
rocks.to_file('rocks.rocks')

rocks_from_disk = SpaceRock.from_file('rocks.rocks')
```

This is useful for saving your work, and getting your exact objects back at a later date.








