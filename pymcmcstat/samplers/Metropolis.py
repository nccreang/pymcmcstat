#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 18 10:30:29 2018

@author: prmiles
"""
# import required packages
import numpy as np
from ..structures.ParameterSet import ParameterSet
from .utilities import sample_candidate_from_gaussian_proposal
from .utilities import is_sample_outside_bounds, set_outside_bounds
from .utilities import acceptance_test
from .utilities import calculate_acceptance_ratio
from .utilities import posterior_ratio_acceptance_test


class Metropolis:
    '''
    .. |br| raw:: html

        <br>

    Pseudo-Algorithm:

        #. Sample :math:`z_k \\sim N(0,1)`
        #. Construct candidate :math:`q^* = q^{k-1} + Rz_k`
        #. Compute |br| :math:`\\quad SS_{q^*} = \\sum_{i=1}^N[v_i-f_i(q^*)]^2`
        #. Compute |br| :math:`\\quad \\alpha = \\min\\Big(1, e^{[SS_{q^*} - SS_{q^{k-1}}]/(2\\sigma^2_{k-1})}\\Big)`
        #. If :math:`u_{\\alpha} <~\\alpha,` |br|
            Set :math:`q^k = q^*,~SS_{q^k} = SS_{q^*}`
           Else
            Set :math:`q^k = q^{k-1},~SS_{q^k} = SS_{q^{k-1}}`

    Attributes:
        * :meth:`~acceptance_test`
        * :meth:`~run_metropolis_step`
        * :meth:`~unpack_set`
    '''
    # --------------------------------------------------------
    def run_metropolis_step(self, old_set, parameters, R,
                            prior_object, like_object, sos_object=None,
                            custom=None):
        '''
        Run Metropolis step.

        Args:
            * **old_set** (:class:`~.ParameterSet`): Features of :math:`q^{k-1}`
            * **parameters** (:class:`~.ModelParameters`): Model parameters
            * **R** (:class:`~numpy.ndarray`): Cholesky decomposition of parameter covariance matrix
            * **priorobj** (:class:`~.PriorFunction`): Prior function
            * **sosobj** (:class:`~.SumOfSquares`): Sum-of-Squares function

        Returns:
            * **accept** (:py:class:`int`): 0 - reject, 1 - accept
            * **newset** (:class:`~.ParameterSet`): Features of :math:`q^*`
            * **outbound** (:py:class:`int`): 1 - rejected due to sampling outside of parameter bounds
            * **npar_sample_from_normal** (:class:`~numpy.ndarray`): Latet random sample points
        '''
        # unpack oldset
        tmp = old_set.__dict__
        oldpar, ss, oldprior, oldlike, sigma2 = (
                tmp['theta'], tmp['ss'], tmp['prior'], tmp['like'], tmp['sigma2'])

        # Sample new candidate from Gaussian proposal
        newpar, npar_sample_from_normal = sample_candidate_from_gaussian_proposal(
                npar=parameters.npar, oldpar=oldpar, R=R)
        # Reject points outside boundaries
        outsidebounds = is_sample_outside_bounds(newpar, parameters._lower_limits[parameters._parind[:]],
                                                 parameters._upper_limits[parameters._parind[:]])
        if outsidebounds is True:
            # proposed value outside parameter limits
            newset = ParameterSet(theta=newpar, sigma2=sigma2)
            newset, outbound = set_outside_bounds(next_set=newset)
            accept = False
        else:
            outbound = 0
            # prior SS for the new theta
            newprior = prior_object.evaluate_prior(newpar)
            # REPLACE SOS WITH LIKELIHOOD OBJECT
            newlike = like_object.evaluate_likelihood(newpar, custom=custom)
            # calculate sum-of-squares
            ss2 = ss  # old ss
            ss1 = sos_object.evaluate_sos_function(newpar, custom=custom)
            q = parameters._initial_value.copy()
            q[parameters._parind] = newpar
            ss1 = like_object.evaluate_sos_function(q, custom=custom)
            # calculate acceptance ratio
#            alpha = calculate_acceptance_ratio(
#                    likestar=newlike,
#                    like=oldlike,
#                    priorstar=newprior,
#                    prior=oldprior)
            # evaluate likelihood
            alpha = self.evaluate_likelihood_function(ss1, ss2, sigma2, newprior, oldprior)
            # make acceptance decision
            accept = acceptance_test(alpha)
#            accept = posterior_ratio_acceptance_test(alpha)
            # store parameter sets in objects
            newset = ParameterSet(theta=newpar, ss=ss1, prior=newprior,
                                  like=newlike, sigma2=sigma2, alpha=alpha)
        return accept, newset, outbound, npar_sample_from_normal

    # --------------------------------------------------------
    @classmethod
    def unpack_set(cls, parset):
        '''
        Unpack parameter set

        Args:
            * **parset** (:class:`~.ParameterSet`): Parameter set to unpack

        Returns:
            * (:class:`:py:class:dict`): Dictionary of parset
        '''
        print('This code is deprecated as of v1.8.0.')
        return parset.__dict__

    # --------------------------------------------------------
    @classmethod
    def evaluate_likelihood_function(cls, ss1, ss2, sigma2, newprior, oldprior):
        '''
        Calculate acceptance ratio:

        .. math::

            \\alpha = \\exp\\Big[-0.5\\Big(\\sum\\Big(\\frac{ SS_{q^*} \
            - SS_{q^{k-1}} }{ \\sigma_{k-1}^2 }\\Big) + p_1 - p_2\\Big)\\Big]

        This is equivalent to calculating the acceptance ratio:

        .. math::

            \\alpha = \\min\\Big[1, \\frac{\\mathcal{L}(\\nu_{obs}|q^*, \
            \\sigma_{k-1}^2)\\pi_0(q^*)}{\\mathcal{L}(\\nu_{obs}|q^{k-1}, \
            \\sigma_{k-1}^2)\\pi_0(q^{k-1})}\\Big]

        where the Gaussian likelihood function is

        .. math::

            \\mathcal{L}(\\nu_{obs}|q, \\sigma) = \
            \\exp\\Big(-\\frac{SS_q}{2\\sigma}\\Big)

        and Gaussian prior function is

        .. math::

            \\pi_0(q) = \\exp \
            \\Big[-\\frac{1}{2}\\Big(\\frac{q - \
            \\mu_0}{\\sigma_0}\\Big)^2\\Big].

        For more details regarding the prior function, please refer to the
        :class:`~.PriorFunction` class.

        .. note::
            The default behavior of the package is to use Gaussian
            likelihood and prior functions (as of v1.7.0).  Future releases
            will expand the functionality to allow for alternative likelihood
            and prior definitions.

        Args:
            * **ss1** (:class:`~numpy.ndarray`): SS error from proposed candidate, :math:`q^*`
            * **ss2** (:class:`~numpy.ndarray`): SS error from previous sample point, :math:`q^{k-1}`
            * **sigma2** (:class:`~numpy.ndarray`): Error variance estimate \
            from previous sample point, :math:`\\sigma_{k-1}^2`
            * **newprior** (:class:`~numpy.ndarray`): Prior for proposal candidate
            * **oldprior** (:class:`~numpy.ndarray`): Prior for previous sample

        Returns:
            * **alpha** (:py:class:`float`): Result of likelihood function
        '''
        alpha = np.exp(-0.5*(sum((ss1 - ss2)*(sigma2**(-1))) + newprior - oldprior))
        return sum(alpha)
