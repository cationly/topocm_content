import itertools
import collections
from functools import reduce
from operator import mul
from copy import copy
from types import SimpleNamespace

import numpy as np
import holoviews as hv

from wraparound import wraparound

if tuple(int(i) for i in np.__version__.split('.')[:3]) <= (1, 8, 0):
    raise RuntimeError("numpy >= (1, 8, 0) is required")

__all__ = ['spectrum', 'hamiltonian_array', 'h_k', 'pauli']

pauli = SimpleNamespace(s0=np.array([[1., 0.], [0., 1.]]),
                        sx=np.array([[0., 1.], [1., 0.]]),
                        sy=np.array([[0., -1j], [1j, 0.]]),
                        sz=np.array([[1., 0.], [0., -1.]]))

pauli.s0s0 = np.kron(pauli.s0, pauli.s0)
pauli.s0sx = np.kron(pauli.s0, pauli.sx)
pauli.s0sy = np.kron(pauli.s0, pauli.sy)
pauli.s0sz = np.kron(pauli.s0, pauli.sz)
pauli.sxs0 = np.kron(pauli.sx, pauli.s0)
pauli.sxsx = np.kron(pauli.sx, pauli.sx)
pauli.sxsy = np.kron(pauli.sx, pauli.sy)
pauli.sxsz = np.kron(pauli.sx, pauli.sz)
pauli.sys0 = np.kron(pauli.sy, pauli.s0)
pauli.sysx = np.kron(pauli.sy, pauli.sx)
pauli.sysy = np.kron(pauli.sy, pauli.sy)
pauli.sysz = np.kron(pauli.sy, pauli.sz)
pauli.szs0 = np.kron(pauli.sz, pauli.s0)
pauli.szsx = np.kron(pauli.sz, pauli.sx)
pauli.szsy = np.kron(pauli.sz, pauli.sy)
pauli.szsz = np.kron(pauli.sz, pauli.sz)


def spectrum(sys, p=None, k_x=None, k_y=None, k_z=None, title=None, xdim=None,
             ydim=None, xticks=None, yticks=None, zticks=None, xlims=None,
             ylims=None):
    """Function that plots system spectrum for varying parameters or momenta.

    Parameters:
    -----------
    sys : kwant.Builder object
        The un-finalized (in)finite system.
    p : SimpleNamespace object
        A container used to store Hamiltonian parameters. The parameters that
        are sequences are used as plot axes.
    k_x, k_y, k_z : floats or sequences of floats
        Real space momenta at which the Hamiltonian has to be evaluated.
        If the system dimensionality is low, extra momenta are ignored.
    title : function
        Function that takes p as argument and generates a string.
    xdim : holoviews.Dimension or string
        The label of the x-axis.
    ydim : holoviews.Dimension or string
        The label of the y-axis. Ignored if only one parameter is changing.
    xticks : list
        List of xticks.
    yticks : list
        List of yticks.
    zticks : list
        List of zticks. Ignored if only one parameter is changing.
    xlims : tupple
        Upper and lower plot limit of the x-axis. If None the upper and lower
        limit of the xticks are used.
    ylims : tupple
        Upper and lower plot limit of the y-axis. If None the upper and lower
        limit of the xticks are used. Ignored if only one parameter is changing.

    Returns:
    --------
    plot : holoviews.Path object
        Plot of varying parameter vs. spectrum.
    """
    pi_ticks = [(-np.pi, r'$-\pi$'), (0, '$0$'), (np.pi, r'$\pi$')]
    if p is None:
        p = SimpleNamespace()
    dimensionality = sys.symmetry.num_directions
    k = [k_x, k_y, k_z]
    k = [(np.linspace(-np.pi, np.pi, 101) if i is None else i)
         for i in k]
    k = [(i if j < dimensionality else 0) for (j, i) in enumerate(k)]
    k_x, k_y, k_z = k

    hamiltonians, variables = hamiltonian_array(sys, p, k_x, k_y, k_z, True)
    # Don't waste effort calculating eigenvalues if we aren't going to plot
    # anything.
    if len(variables) in (1, 2):
        energies = np.linalg.eigvalsh(hamiltonians)

    if len(variables) == 0:
        raise ValueError("A 0D plot requested")

    elif len(variables) == 1:
        # 1D plot.
        if xdim is None:
            xdim = 'x'
        if ydim is None:
            ydim = 'y'

        plot = hv.Path((variables[0][1], energies), kdims=[xdim, ydim])

        ticks = {}
        if isinstance(xticks, collections.Iterable):
            ticks['xticks'] = list(xticks)
        elif xticks is None:
            pass
        else:
            ticks['xticks'] = xticks

        if isinstance(yticks, collections.Iterable):
            ticks['yticks'] = list(yticks)
        elif isinstance(yticks, int):
            ticks['yticks'] = yticks

        xlims = slice(*xlims) if xlims is not None else slice(None)
        ylims = slice(*ylims) if ylims is not None else slice(None)

        if callable(title):
            plot = plot.relabel(title(p))

        return plot[xlims, ylims](plot={'Path': ticks})

    elif len(variables) == 2:
        # 2D plot.

        style = {}
        if xticks is None and variables[0][0] in 'k_x k_y k_z'.split():
            style['xticks'] = pi_ticks
        if yticks is None and variables[1][0] in 'k_x k_y k_z'.split():
            style['yticks'] = pi_ticks
        if zticks is not None:
            style['zticks'] = zticks

        if xlims is None:
            xlims = np.round([min(variables[0][1]), max(variables[0][1])], 2)
        if ylims is None:
            ylims = np.round([min(variables[0][1]), max(variables[0][1])], 2)

            kwargs = {'extents': (xlims[0], ylims[0], None,
                                  xlims[1], ylims[1], None),
                      'kdims': [r'$k_x$', r'$k_y$'],
                      'vdims': [r'$E$']}

        plot = reduce(mul, (hv.Surface(energies[:, :, i], **kwargs)(plot=style)
                            for i in range(energies.shape[-1])))

        if callable(title):
            plot = plot.relabel(title(p))

        return plot(plot={'Overlay': {'fig_size': 200}})

    else:
        raise ValueError("Cannot make 4D plots yet.")



def h_k(sys, p, momentum):
    """Function that returns the Hamiltonian of a kwant 1D system as a momentum.
    """
    return hamiltonian_array(sys, p, momentum)[0]


def hamiltonian_array(sys, p=None, k_x=0, k_y=0, k_z=0, return_grid=False):
    """Evaluate the Hamiltonian of a system over a grid of parameters.

    Parameters:
    -----------
    sys : kwant.Builder object
        The un-finalized kwant system whose Hamiltonian is calculated.
    p : SimpleNamespace object
        A container of Hamiltonian parameters. The parameters that are
        sequences are used to loop over.
    k_x, k_y, k_z : floats or sequences of floats
        Real space momenta at which the Hamiltonian has to be evaluated.
        If the system dimensionality is low, extra momenta are ignored.
    return_grid : bool
        Whether to also return the names of the variables used for expansion,
        and their values.

    Returns:
    --------
    hamiltonians : numpy.ndarray
        An array with the Hamiltonians. The first n-2 dimensions correspond to
        the expanded variables.
    parameters : list of tuples
        Names and ranges of values that were used in evaluation of the
        Hamiltonians.

    Examples:
    ---------
    >>> hamiltonian_array(sys, SimpleNamespace(t=1, mu=np.linspace(-2, 2)),
    ...                   k_x=np.linspace(-np.pi, np.pi))
    >>> hamiltonian_array(sys_2d, p, np.linspace(-np.pi, np.pi),
    ...                   np.linspace(-np.pi, np.pi))
    """
    if p is None:
        p = SimpleNamespace()
    try:
        space_dimensionality = sys.symmetry.periods.shape[-1]
    except AttributeError:
        space_dimensionality = 0
    dimensionality = sys.symmetry.num_directions
    pars = copy(p)
    if dimensionality == 0:
        sys = sys.finalized()
        def momentum_to_lattice(k):
            return []
    else:
        B = np.array(sys.symmetry.periods).T
        A = B.dot(np.linalg.inv(B.T.dot(B)))
        def momentum_to_lattice(k):
            k, residuals, *_ = np.linalg.lstsq(A, k[:space_dimensionality])
            if np.any(abs(residuals) > 1e-7):
                raise RuntimeError("Requested momentum doesn't correspond"
                                   " to any lattice momentum.")
            return list(k)
        sys = wraparound(sys).finalized()

    changing = dict()
    for key, value in pars.__dict__.items():
        if isinstance(value, collections.Iterable):
            changing[key] = value

    for key, value in [('k_x', k_x), ('k_y', k_y), ('k_z', k_z)]:
        if key in changing:
            raise RuntimeError('One of the system parameters is {}, '
                               'which is reserved for momentum. '
                               'Please rename it.'.format(key))
        if isinstance(value, collections.Iterable):
            changing[key] = value

    if not changing:
        return sys.hamiltonian_submatrix([pars] +
                                         momentum_to_lattice([k_x, k_y, k_z]),
                                         sparse=False)[None, ...]

    def hamiltonian(**values):
        pars.__dict__.update(values)
        k = [values.get('k_x', k_x), values.get('k_y', k_y),
             values.get('k_z', k_z)]
        k = momentum_to_lattice(k)
        return sys.hamiltonian_submatrix(args=([pars] + k), sparse=False)

    names, values = zip(*sorted(changing.items()))
    hamiltonians = [hamiltonian(**dict(zip(names, value)))
                    for value in itertools.product(*values)]
    size = list(hamiltonians[0].shape)

    hamiltonians = np.array(hamiltonians).reshape([len(value)
                                                   for value in values] + size)

    if return_grid:
        return hamiltonians, list(zip(names, values))
    else:
        return hamiltonians
