from __future__ import print_function
import unittest
import numpy as np
import discretize
from SimPEG import (
    maps, utils, data_misfit, regularization,
    optimization, tests, inversion, inverse_problem
)
from SimPEG.electromagnetics import resistivity as dc
try:
    from pymatsolver import Pardiso as Solver
except ImportError:
    from SimPEG import SolverLU as Solver

np.random.seed(41)


class DCProblem_2DTestsCC(unittest.TestCase):

    formulation = 'Problem2D_CC'
    storeJ = False
    adjoint_tol = 1e-10

    def setUp(self):
        print("\n  ---- Testing {} ---- \n".format(self.formulation))
        cs = 12.5
        hx = [(cs, 2, -1.3), (cs, 61), (cs, 2, 1.3)]
        hy = [(cs, 2, -1.3), (cs, 20)]
        mesh = discretize.TensorMesh([hx, hy], x0="CN")
        x = np.linspace(-135, 250., 20)
        M = utils.ndgrid(x-12.5, np.r_[0.])
        N = utils.ndgrid(x+12.5, np.r_[0.])
        A0loc = np.r_[-150, 0.]
        A1loc = np.r_[-130, 0.]
        # rxloc = [np.c_[M, np.zeros(20)], np.c_[N, np.zeros(20)]]
        rx = dc.Rx.Dipole_ky(M, N)
        src0 = dc.Src.Pole([rx], A0loc)
        src1 = dc.Src.Pole([rx], A1loc)
        survey = dc.Survey_ky([src0, src1])
        problem = getattr(dc, self.formulation)(
            mesh, rhoMap=maps.IdentityMap(mesh), storeJ=self.storeJ,
            solver=Solver, survey=survey
        )
        mSynth = np.ones(mesh.nC)*1.
        data = problem.make_synthetic_data(mSynth)

        # Now set up the problem to do some minimization
        dmis = data_misfit.L2DataMisfit(simulation=problem, data=data)
        reg = regularization.Tikhonov(mesh)
        opt = optimization.InexactGaussNewton(
            maxIterLS=20, maxIter=10, tolF=1e-6,
            tolX=1e-6, tolG=1e-6, maxIterCG=6
        )
        invProb = inverse_problem.BaseInvProblem(dmis, reg, opt, beta=1e0)
        inv = inversion.BaseInversion(invProb)

        self.inv = inv
        self.reg = reg
        self.p = problem
        self.mesh = mesh
        self.m0 = mSynth
        self.survey = survey
        self.dmis = dmis
        self.data = data

    def test_misfit(self):
        passed = tests.checkDerivative(
            lambda m: (
                self.p.dpred(m), lambda mx: self.p.Jvec(self.m0, mx)
            ),
            self.m0,
            plotIt=False,
            num=3
        )
        self.assertTrue(passed)

    def test_adjoint(self):
        # Adjoint Test
        # u = np.random.rand(self.mesh.nC * self.survey.nSrc)
        v = np.random.rand(self.mesh.nC)
        w = np.random.rand(self.data.nD)
        wtJv = w.dot(self.p.Jvec(self.m0, v))
        vtJtw = v.dot(self.p.Jtvec(self.m0, w))
        passed = np.abs(wtJv - vtJtw) < self.adjoint_tol
        print('Adjoint Test', np.abs(wtJv - vtJtw), passed)
        self.assertTrue(passed)

    def test_dataObj(self):
        passed = tests.checkDerivative(
            lambda m: [self.dmis(m), self.dmis.deriv(m)],
            self.m0,
            plotIt=False,
            num=3
        )
        self.assertTrue(passed)


class DCProblemTestsN(DCProblem_2DTestsCC):

    formulation = 'Problem2D_N'
    storeJ = False
    adjoint_tol = 1e-8


class DCProblem_2DTestsCC_storeJ(DCProblem_2DTestsCC):

    formulation = 'Problem2D_CC'
    storeJ = True
    adjoint_tol = 1e-10


class DCProblemTestsN_storeJ(DCProblem_2DTestsCC):

    formulation = 'Problem2D_N'
    storeJ = True
    adjoint_tol = 1e-8

if __name__ == '__main__':
    unittest.main()
