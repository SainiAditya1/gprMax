# Copyright (C) 2015-2023: The University of Edinburgh, United Kingdom
#                 Authors: Craig Warren, Antonis Giannopoulos, and John Hartley
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

import numpy as np

from ..fractals import FractalSurface, Grass
from ..materials import create_grass
from ..utilities.utilities import round_value
from .cmds_geometry import UserObjectGeometry, rotate_2point_object

logger = logging.getLogger(__name__)


class AddGrass(UserObjectGeometry):
    """Adds grass with roots to a FractalBox class in the model.

    Attributes:
        p1: list of the lower left (x,y,z) coordinates of a surface on a
            FractalBox class.
        p2: list of the upper right (x,y,z) coordinates of a surface on a
            FractalBox class.
        frac_dim: float for the fractal dimension which, for an orthogonal
                    parallelepiped, should take values between zero and three.
        limits: list to define lower and upper limits for a range over which
                    the height of the blades of grass can vary.
        n_blades:int for the number of blades of grass that should be
                    applied to the surface area.
        fractal_box_id: string identifier for the FractalBox class that the
                        grass should be applied to.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hash = "#add_grass"

    def rotate(self, axis, angle, origin=None):
        """Set parameters for rotation."""
        self.axis = axis
        self.angle = angle
        self.origin = origin
        self.do_rotate = True

    def _do_rotate(self):
        """Perform rotation."""
        pts = np.array([self.kwargs["p1"], self.kwargs["p2"]])
        rot_pts = rotate_2point_object(pts, self.axis, self.angle, self.origin)
        self.kwargs["p1"] = tuple(rot_pts[0, :])
        self.kwargs["p2"] = tuple(rot_pts[1, :])

    def create(self, grid, uip):
        """Add Grass to fractal box."""
        try:
            p1 = self.kwargs["p1"]
            p2 = self.kwargs["p2"]
            fractal_box_id = self.kwargs["fractal_box_id"]
            frac_dim = self.kwargs["frac_dim"]
            limits = self.kwargs["limits"]
            n_blades = self.kwargs["n_blades"]
        except KeyError:
            logger.exception(f"{self.__str__()} requires at least eleven parameters")
            raise

        try:
            seed = self.kwargs["seed"]
        except KeyError:
            seed = None

        if self.do_rotate:
            self._do_rotate()

        # Get the correct fractal volume
        volumes = [volume for volume in grid.fractalvolumes if volume.ID == fractal_box_id]
        try:
            volume = volumes[0]
        except NameError:
            logger.exception(f"{self.__str__()} cannot find FractalBox {fractal_box_id}")
            raise

        p1, p2 = uip.check_box_points(p1, p2, self.__str__())
        xs, ys, zs = p1
        xf, yf, zf = p2

        if frac_dim < 0:
            logger.exception(f"{self.__str__()} requires a positive value for " + "the fractal dimension")
            raise ValueError
        if limits[0] < 0 or limits[1] < 0:
            logger.exception(
                f"{self.__str__()} requires a positive value for " + "the minimum and maximum heights for grass blades"
            )
            raise ValueError

        # Check for valid orientations
        if xs == xf:
            if ys == yf or zs == zf:
                logger.exception(f"{self.__str__()} dimensions are not specified correctly")
                raise ValueError
            if xs not in [volume.xs, volume.xf]:
                logger.exception(f"{self.__str__()} must specify external surfaces on a fractal box")
                raise ValueError
            fractalrange = (round_value(limits[0] / grid.dx), round_value(limits[1] / grid.dx))
            # xminus surface
            if xs == volume.xs:
                logger.exception(
                    f"{self.__str__()} grass can only be specified " + "on surfaces in the positive axis direction"
                )
                raise ValueError
            # xplus surface
            elif xf == volume.xf:
                if fractalrange[1] > grid.nx:
                    logger.exception(
                        f"{self.__str__()} cannot apply grass to "
                        + "fractal box as it would exceed the domain "
                        + "size in the x direction"
                    )
                    raise ValueError
                requestedsurface = "xplus"

        elif ys == yf:
            if zs == zf:
                logger.exception(f"{self.__str__()} dimensions are not specified correctly")
                raise ValueError
            if ys not in [volume.ys, volume.yf]:
                logger.exception(f"{self.__str__()} must specify external surfaces on a fractal box")
                raise ValueError
            fractalrange = (round_value(limits[0] / grid.dy), round_value(limits[1] / grid.dy))
            # yminus surface
            if ys == volume.ys:
                logger.exception(
                    f"{self.__str__()} grass can only be specified " + "on surfaces in the positive axis direction"
                )
                raise ValueError
            # yplus surface
            elif yf == volume.yf:
                if fractalrange[1] > grid.ny:
                    logger.exception(
                        f"{self.__str__()} cannot apply grass to "
                        + "fractal box as it would exceed the domain "
                        + "size in the y direction"
                    )
                    raise ValueError
                requestedsurface = "yplus"

        elif zs == zf:
            if zs not in [volume.zs, volume.zf]:
                logger.exception(f"{self.__str__()} must specify external surfaces on a fractal box")
                raise ValueError
            fractalrange = (round_value(limits[0] / grid.dz), round_value(limits[1] / grid.dz))
            # zminus surface
            if zs == volume.zs:
                logger.exception(
                    f"{self.__str__()} grass can only be specified " + "on surfaces in the positive axis direction"
                )
                raise ValueError
            # zplus surface
            elif zf == volume.zf:
                if fractalrange[1] > grid.nz:
                    logger.exception(
                        f"{self.__str__()} cannot apply grass to "
                        + "fractal box as it would exceed the domain "
                        + "size in the z direction"
                    )
                    raise ValueError
                requestedsurface = "zplus"

        else:
            logger.exception(f"{self.__str__()} dimensions are not specified correctly")
            raise ValueError

        surface = FractalSurface(xs, xf, ys, yf, zs, zf, frac_dim)
        surface.ID = "grass"
        surface.surfaceID = requestedsurface
        surface.seed = seed

        # Set the fractal range to scale the fractal distribution between zero and one
        surface.fractalrange = (0, 1)
        surface.operatingonID = volume.ID
        surface.generate_fractal_surface()
        if n_blades > surface.fractalsurface.shape[0] * surface.fractalsurface.shape[1]:
            logger.exception(
                f"{self.__str__()} the specified surface is not large "
                + "enough for the number of grass blades/roots specified"
            )
            raise ValueError

        # Scale the distribution so that the summation is equal to one,
        # i.e. a probability distribution
        surface.fractalsurface = surface.fractalsurface / np.sum(surface.fractalsurface)

        # Set location of grass blades using probability distribution
        # Create 1D vector of probability values from the 2D surface
        probability1D = np.cumsum(np.ravel(surface.fractalsurface))

        # Create random numbers between zero and one for the number of blades of grass
        R = np.random.RandomState(surface.seed)
        A = R.random_sample(n_blades)

        # Locate the random numbers in the bins created by the 1D vector of
        # probability values, and convert the 1D index back into a x, y index
        # for the original surface.
        bladesindex = np.unravel_index(
            np.digitize(A, probability1D), (surface.fractalsurface.shape[0], surface.fractalsurface.shape[1])
        )

        # Set the fractal range to minimum and maximum heights of the grass blades
        surface.fractalrange = fractalrange

        # Set the fractal surface using the pre-calculated spatial distribution
        # and a random height
        surface.fractalsurface = np.zeros((surface.fractalsurface.shape[0], surface.fractalsurface.shape[1]))
        for i in range(len(bladesindex[0])):
            surface.fractalsurface[bladesindex[0][i], bladesindex[1][i]] = R.randint(
                surface.fractalrange[0], surface.fractalrange[1], size=1
            )

        # Create grass geometry parameters
        g = Grass(n_blades)
        g.seed = surface.seed
        surface.grass.append(g)

        # Check to see if grass has been already defined as a material
        if not any(x.ID == "grass" for x in grid.materials):
            create_grass(grid)

        # Check if time step for model is suitable for using grass
        grass = next((x for x in grid.materials if x.ID == "grass"))
        testgrass = next((x for x in grass.tau if x < grid.dt), None)
        if testgrass:
            logger.exception(
                f"{self.__str__()} requires the time step for the "
                + "model to be less than the relaxation time required to model grass."
            )
            raise ValueError

        volume.fractalsurfaces.append(surface)

        logger.info(
            f"{self.grid_name(grid)}{n_blades} blades of grass on surface from "
            + f"{xs * grid.dx:g}m, {ys * grid.dy:g}m, {zs * grid.dz:g}m, "
            + f"to {xf * grid.dx:g}m, {yf * grid.dy:g}m, {zf * grid.dz:g}m "
            + f"with fractal dimension {surface.dimension:g}, fractal seeding "
            + f"{surface.seed}, and range {limits[0]:g}m to {limits[1]:g}m, "
            + f"added to {surface.operatingonID}."
        )
