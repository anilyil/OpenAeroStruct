from __future__ import print_function
import numpy as np
import matplotlib.pyplot as plt

from openmdao.api import Problem, IndepVarComp, pyOptSparseDriver, view_model, Group, ExecComp

from openaerostruct_v2.geometry.inputs_group import InputsGroup
from openaerostruct_v2.structures.fea_bspline_group import FEABsplineGroup
from openaerostruct_v2.structures.fea_preprocess_group import FEAPreprocessGroup
from openaerostruct_v2.structures.fea_states_group import FEAStatesGroup
from openaerostruct_v2.structures.fea_postprocess_group import FEAPostprocessGroup


num_nodes = 2

num_points_x = 2
num_points_z_half = 15
num_points_z = 2 * num_points_z_half - 1
lifting_surfaces = [
    ('wing', {
        'num_points_x': num_points_x, 'num_points_z_half': num_points_z_half,
        'airfoil': np.zeros(num_points_x),
        'chord': 1., 'twist': 0. * np.pi / 180., 'sweep_x': 0., 'dihedral_y': 0., 'span': 5,
        'twist_bspline': (2, 2),
        'sec_z_bspline': (num_points_z_half, 2),
        'chord_bspline': (2, 2),
        'thickness_bspline': (10, 3),
        'thickness' : .1,
        'radius' : 1.,
        'distribution': 'sine',
    })
]
wing_data = {
    'section_origin': 0.25,
    'spar_location': 0.35,
    'E': 70.e9,
    'G': 29.e9,
    'lifting_surfaces': lifting_surfaces,
    'airfoil': np.zeros(num_points_x),
}

wing_loads = np.zeros((num_nodes, num_points_z, 6))
wing_loads[0, :, 1] = 1.
if num_nodes > 1:
    wing_loads[1, :, 0] = 1.

prob = Problem()
prob.model = Group()

indep_var_comp = IndepVarComp()
indep_var_comp.add_output('v_m_s', shape=num_nodes, val=200.)
indep_var_comp.add_output('alpha_rad', shape=num_nodes, val=3. * np.pi / 180.)
indep_var_comp.add_output('rho_kg_m3', shape=num_nodes, val=1.225)
indep_var_comp.add_output('wing_loads', val=wing_loads)
prob.model.add_subsystem('indep_var_comp', indep_var_comp, promotes=['*'])

inputs_group = InputsGroup(num_nodes=num_nodes, wing_data=wing_data)
prob.model.add_subsystem('inputs_group', inputs_group, promotes=['*'])

prob.model.add_subsystem('tube_bspline_group',
    FEABsplineGroup(num_nodes=num_nodes, wing_data=wing_data),
    promotes=['*'])

prob.model.add_subsystem('fea_preprocess_group',
    FEAPreprocessGroup(num_nodes=num_nodes, wing_data=wing_data),
    promotes=['*'],
)
prob.model.add_subsystem('fea_states_group',
    FEAStatesGroup(num_nodes=num_nodes, wing_data=wing_data),
    promotes=['*'],
)
prob.model.add_subsystem('fea_postprocess_group',
    FEAPostprocessGroup(num_nodes=num_nodes, wing_data=wing_data),
    promotes=['*'],
)
prob.model.add_subsystem('objective',
    ExecComp('obj=1000*sum(compliance)', compliance=np.zeros(num_nodes)),
    promotes=['*'],
)

prob.model.add_design_var('wing_tube_thickness_dv', lower=0.01)
prob.model.add_objective('obj')
prob.model.add_constraint('structural_volume', upper=10)

prob.driver = pyOptSparseDriver()
prob.driver.options['optimizer'] = 'SNOPT'
prob.driver.opt_settings['Major optimality tolerance'] = 2e-7
prob.driver.opt_settings['Major feasibility tolerance'] = 2e-7

prob.setup()

prob['wing_chord_dv'] = [0.5, 1.0, 0.5]

prob.run_model()

if 0:
    prob.check_partials(compact_print=True)
    exit()

print(prob['structural_volume'])

prob.run_driver()

print(prob['wing_tube_thickness'])

print(prob['wing_disp'])

import matplotlib.pyplot as plt

for i in range(num_nodes):
    x = prob['wing_fea_mesh'][i, :]
    xx = 0.5 * x[:-1] + 0.5 * x[1:]
    plt.subplot(num_nodes, 3, 3*i + 1)
    plt.plot(xx, prob['wing_tube_thickness'][i, :])
    plt.subplot(num_nodes, 3, 3*i + 2)
    plt.plot(x, prob['wing_disp'][i, :, 0])
    plt.subplot(num_nodes, 3, 3*i + 3)
    plt.plot(x, prob['wing_disp'][i, :, 1])
plt.show()
