from .spacerock import SpaceRock
from .spice import SpiceBody
from .model import PerturberModel
from .units import Units
from .convenience import Convenience

import copy
import numpy as np
from rich.progress import track

import rebound
from rebound.units import masses_SI, lengths_SI, times_SI
from astropy import units as u
from astropy.time import Time

def get_rebound_unit_representation(unit, rebound_values) -> str:
    if isinstance(unit, str):
        return {unit}.intersection(set(rebound_values.keys())).pop()
    return set([x.lower() for x in unit._names]).intersection(set(rebound_values.keys())).pop()

def create_rebound_units(units: Units) -> tuple:
    mass_units = get_rebound_unit_representation(units.mass, masses_SI)
    length_units = get_rebound_unit_representation(units.distance, lengths_SI)
    time_units = get_rebound_unit_representation(units.time, times_SI)
    return (mass_units, length_units, time_units)


class Simulation(rebound.Simulation, Convenience):

    def __init__(self, model='GIANTS', units=Units(), **kwargs):
        super().__init__(self)
        self.spacerocks_units = units
        self.units = create_rebound_units(self.spacerocks_units)

        if isinstance(model, str):
            self.model = PerturberModel.from_builtin(model)
        elif isinstance(model, PerturberModel):
            self.model = model

        self.perturber_names = list(self.model.perturbers)
        self.testparticle_names = []
        self.remaining_testparticles = []
        self.N_active = len(self.perturber_names)
        
        self.simdata = {}
        
        if kwargs.get('epoch') is not None:
            if isinstance(kwargs.get('epoch'), str):
                self.epoch = self.detect_timescale([kwargs.get('epoch')], self.spacerocks_units.timescale)
            else:
                self.epoch = Time(kwargs.get('epoch'), 
                                  format=self.spacerocks_units.timeformat, 
                                  scale=self.spacerocks_units.timescale)

        self.t = copy.deepcopy(self.epoch.tdb.jd)
        for name, perturber in self.model.perturbers.items():
            if isinstance(perturber, SpaceRock):
                if hasattr(perturber, 'epoch'):
                    body = perturber.analytic_propagate(self.epoch)
                    self.add(x=body.x.au[0], 
                             y=body.y.au[0], 
                             z=body.z.au[0],
                             vx=body.vx.value[0], 
                             vy=body.vy.value[0], 
                             vz=body.vz.value[0],
                             m=body.mass.to(self.spacerocks_units.mass).value[0], 
                             hash=name)
                else:
                    self.add(x=body.x.au[0], 
                             y=body.y.au[0], 
                             z=body.z.au[0],
                             vx=body.vx.value[0], 
                             vy=body.vy.value[0], 
                             vz=body.vz.value[0],
                             m=body.mass.to(self.spacerocks_units.mass).value[0], 
                             hash=name)
                    
            elif isinstance(perturber, SpiceBody):
                body = perturber.at(self.epoch)
                self.add(x=body.x.au[0], 
                         y=body.y.au[0], 
                         z=body.z.au[0],
                         vx=body.vx.value[0], 
                         vy=body.vy.value[0], 
                         vz=body.vz.value[0],
                         m=perturber.mass.to(self.spacerocks_units.mass).value, 
                         hash=name)
                
        for n in self.perturber_names:
            h = self.particles[n].hash
            self.simdata[h.value] = []

        self.move_to_com()
        
    def add_spacerocks(self, rocks):
        r = copy.deepcopy(rocks)
        self.testparticle_names += copy.deepcopy(r.name.tolist())
        self.remaining_testparticles += copy.deepcopy(r.name.tolist())
        r.to_bary()
        r.change_frame('eclipJ2000')
       
        if hasattr(r, 'epoch'):       
            # Integrate all particles to the same epoch
            pickup_times = r.epoch.tdb.jd
            
            for time in np.sort(np.unique(pickup_times)):
                self.integrate(time, exact_finish_time=1)
                ps = r[r.epoch.tdb.jd == time]
                for x, y, z, vx, vy, vz, name in zip(ps.x.value, ps.y.value, ps.z.value, ps.vx.value, ps.vy.value, ps.vz.value, ps.name):
                    self.add(x=x, y=y, z=z, vx=vx, vy=vy, vz=vz, m=0, hash=name)
                    
        else:
            for rock, name in zip(r, r.name):
                self.add(x=rock.x.au, 
                         y=rock.y.au, 
                         z=rock.z.au,
                         vx=rock.vx.value, 
                         vy=rock.vy.value, 
                         vz=rock.vz.value,
                         m=0, 
                         hash=name)
        
        for n in r.name:
            h = self.particles[n].hash
            self.simdata[h.value] = []
            
    def propagate(self, epochs, units=Units(), progress=True, exact_finish_time=1, **kwargs):
        '''
        Numerically integrate all bodies to the desired date.
        This routine synchronizes the epochs.
        '''

        if kwargs.get('callback') is not None:
            f = True
            callback = kwargs.get('callback')
        else:
            f = False

        epochs = self.detect_timescale(np.atleast_1d(epochs), units.timescale)

        if progress == True:
            iterator = track(np.sort(epochs.tdb.jd))
        else:
            iterator = np.sort(epochs.tdb.jd)
        
        for time in iterator:
            self.integrate(time, exact_finish_time=exact_finish_time)

            if f == True:
                callback(self)
            
            for p in self.particles:
                h = p.hash.value
                arr = [time] + p.xyz + p.vxyz
                self.simdata[h].append(arr)

        pepoch  = []
        px      = []
        py      = []
        pz      = []
        pvx     = []
        pvy     = []
        pvz     = []
        pname   = []
        for n in self.perturber_names:
            ts, xs, ys, zs, vxs, vys, vzs = np.array(self.simdata[rebound.hash(n).value]).T
            pepoch.append(ts.tolist())
            px.append(xs.tolist())
            py.append(ys.tolist())
            pz.append(zs.tolist())
            pvx.append(vxs.tolist())
            pvy.append(vys.tolist())
            pvz.append(vzs.tolist())
            pname.append([n for _ in range(len(ts))])

        pepoch  = np.hstack(pepoch)
        px      = np.hstack(px)
        py      = np.hstack(py)
        pz      = np.hstack(pz)
        pvx     = np.hstack(pvx)
        pvy     = np.hstack(pvy)
        pvz     = np.hstack(pvz)
        pname   = np.hstack(pname)
           
        planets = SpaceRock(x=px, y=py, z=pz, vx=pvx, vy=pvy, vz=pvz, name=pname, epoch=pepoch, origin='ssb', units=units)

        if hasattr(self, 'testparticle_names'):
            epoch  = []
            x      = []
            y      = []
            z      = []
            vx     = []
            vy     = []
            vz     = []
            name   = []
            for n in self.testparticle_names:
                try:
                    ts, xs, ys, zs, vxs, vys, vzs = np.array(self.simdata[rebound.hash(n).value]).T
                except ValueError:
                    continue
                epoch.append(ts.tolist())
                x.append(xs.tolist())
                y.append(ys.tolist())
                z.append(zs.tolist())
                vx.append(vxs.tolist())
                vy.append(vys.tolist())
                vz.append(vzs.tolist())
                name.append([n for _ in range(len(ts))])

            epoch  = np.hstack(epoch)
            x      = np.hstack(x)
            y      = np.hstack(y)
            z      = np.hstack(z)
            vx     = np.hstack(vx)
            vy     = np.hstack(vy)
            vz     = np.hstack(vz)
            name   = np.hstack(name)

            rocks = SpaceRock(x=x, y=y, z=z, vx=vx, vy=vy, vz=vz, name=name, epoch=epoch, origin='ssb', units=units)

        else:
            rocks = ()
        
        return rocks, planets, self