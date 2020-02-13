# Copyright (C) 2015-2020: The University of Edinburgh
#                 Authors: Craig Warren and Antonis Giannopoulos
#
# This file is part of gprMax.
#
# gprMax is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# gprMax is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gprMax.  If not, see <http://www.gnu.org/licenses/>.

import logging
from pathlib import Path

import h5py

import gprMax.config as config
from .cmds_geometry import UserObjectGeometry
from ..cython.geometry_primitives import build_voxels_from_array
from ..exceptions import CmdInputError
from ..hash_cmds_file import get_user_objects
from ..utilities import round_value

log = logging.getLogger(__name__)


class GeometryObjectsRead(UserObjectGeometry):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.order = 1
        self.hash = '#geometry_objects_read'

    def create(self, G, uip):
        """Create the object and add it to the grid."""
        try:
            p1 = self.kwargs['p1']
            geofile = self.kwargs['geofile']
            matfile = self.kwargs['matfile']
        except:
            raise CmdInputError(self.__str__() + 'requires exactly five parameters')

        # discretise the point using uip object. This has different behaviour
        # depending on the type of uip object. So we can use it for
        # the main grid or the subgrid.
        xs, ys, zs = uip.discretise_point(p1)

        # See if material file exists at specified path and if not try input
        # file directory
        matfile = Path(matfile)

        if not matfile.exists():
            matfile = Path(config.sim_config.input_file_path.parent, matfile)

        matstr = matfile.with_suffix('').name
        numexistmaterials = len(G.materials)

        # Read materials from file
        with open(matfile, 'r') as f:
            # Read any lines that begin with a hash. Strip out any newline
            # characters and comments that must begin with double hashes.
            materials = [line.rstrip() + '{' + matstr + '}\n' for line in f if(line.startswith('#') and not line.startswith('##') and line.rstrip('\n'))]

        # build scene
        # API for multiple scenes / model runs
        scene = config.get_model_config().get_scene()
        material_objs = get_user_objects(materials, check=False)
        for material_obj in material_objs:
            scene.add(material_obj)

        # Creates the internal simulation objects
        scene.process_cmds(material_objs, G, sort=False)

        # Update material type
        for material in G.materials:
            if material.numID >= numexistmaterials:
                if material.type:
                    material.type += ',\nimported'
                else:
                    material.type = 'imported'

        # See if geometry object file exists at specified path and if not try input file directory
        geofile = Path(geofile)
        if not geofile.exists():
            geofile = Path(config.sim_config.input_file_path.parent, geofile)

        # Open geometry object file and read/check spatial resolution attribute
        f = h5py.File(geofile, 'r')
        dx_dy_dz = f.attrs['dx_dy_dz']
        if round_value(dx_dy_dz[0] / G.dx) != 1 or round_value(dx_dy_dz[1] / G.dy) != 1 or round_value(dx_dy_dz[2] / G.dz) != 1:
            raise CmdInputError(self.__str__() + ' requires the spatial resolution of the geometry objects file to match the spatial resolution of the model')

        data = f['/data'][:]

        # Should be int16 to allow for -1 which indicates background, i.e.
        # don't build anything, but AustinMan/Woman maybe uint16
        if data.dtype != 'int16':
            data = data.astype('int16')

        # Look to see if rigid and ID arrays are present (these should be
        # present if the original geometry objects were written from gprMax)
        try:
            rigidE = f['/rigidE'][:]
            rigidH = f['/rigidH'][:]
            ID = f['/ID'][:]
            G.solid[xs:xs + data.shape[0], ys:ys + data.shape[1], zs:zs + data.shape[2]] = data + numexistmaterials
            G.rigidE[:, xs:xs + rigidE.shape[1], ys:ys + rigidE.shape[2], zs:zs + rigidE.shape[3]] = rigidE
            G.rigidH[:, xs:xs + rigidH.shape[1], ys:ys + rigidH.shape[2], zs:zs + rigidH.shape[3]] = rigidH
            G.ID[:, xs:xs + ID.shape[1], ys:ys + ID.shape[2], zs:zs + ID.shape[3]] = ID + numexistmaterials
            log.info(f'Geometry objects from file {geofile} inserted at {xs * G.dx:g}m, {ys * G.dy:g}m, {zs * G.dz:g}m, with corresponding materials file {matfile}.')
        except KeyError:
            averaging = False
            build_voxels_from_array(xs, ys, zs, numexistmaterials, averaging, data, G.solid, G.rigidE, G.rigidH, G.ID)
            log.info(f'Geometry objects from file (voxels only){geofile} inserted at {xs * G.dx:g}m, {ys * G.dy:g}m, {zs * G.dz:g}m, with corresponding materials file {matfile}.')