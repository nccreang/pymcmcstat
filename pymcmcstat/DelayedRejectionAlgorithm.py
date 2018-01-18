#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Thu Jan 18 10:42:07 2018

@author: prmiles
"""
# import required packages
import numpy as np
from ParameterSet import ParameterSet

class DelayedRejectionAlgorithm:
        # -------------------------------------------
    def run_delayed_rejection(self, old_set, new_set, RDR, ntry, parameters,
                              invR, sosobj, priorobj):
        # create trypath
        trypath = [old_set, new_set]
        itry = 1; # dr step index
        accept = 0 # initialize acceptance criteria
        while accept == 0 and itry < ntry:
            itry = itry + 1 # update dr step index
            # initialize next step parameter set
            next_set = ParameterSet()
            u = np.random.randn(1,parameters.npar) # u
            next_set.theta = old_set.theta + np.dot(u,RDR[itry-1])
            next_set.theta = next_set.theta.reshape(parameters.npar)
            next_set.sigma2 = new_set.sigma2
                    
            # Reject points outside boundaries
            if (next_set.theta < parameters.lower_limits[parameters.parind[:]]).any() or (next_set.theta > parameters.upper_limits[parameters.parind[:]]).any():
                next_set.alpha = 0
                next_set.prior = 0
                next_set.ss = np.inf
                trypath.append(next_set)
                outbound = 1
                out_set = old_set
                continue
                    
            # Evaluate new proposals
            outbound = 0
            next_set.ss = sosobj.evaluate_sos_function(next_set.theta)
            next_set.prior = priorobj.evaluate_prior(next_set.theta)
            trypath.append(next_set) # add set to trypath
            alpha = self.alphafun(trypath, invR)
            trypath[-1].alpha = alpha # add propability ratio
                           
            # check results of delayed rejection
            # u2 = np.random.rand(1)
            if alpha >= 1 or np.random.rand(1) < alpha: # accept
                accept = 1
                out_set = next_set
                self.iacce[itry-1] += 1 # number accepted from DR
            else:
                out_set = old_set
                
        return accept, out_set, outbound
    
    def initialize_dr_metrics(self, options):
        self.iacce = np.zeros(options.ntry)
        self.dr_step_counter = 0
    
    def alphafun(self, trypath, invR):
        self.dr_step_counter = self.dr_step_counter + 1
        stage = len(trypath) - 1 # The stage we're in, elements in trypath - 1
        # recursively compute past alphas
        a1 = 1 # initialize
        a2 = 1 # initialize
        for k in range(0,stage-1):
            tmp1 = self.alphafun(trypath[0:(k+2)], invR)
            a1 = a1*(1 - tmp1)
            tmp2 = self.alphafun(trypath[stage:stage-k-2:-1], invR)
            a2 = a2*(1 - tmp2)
            if a2 == 0: # we will come back with prob 1
                alpha = np.zeros(1)
                return alpha
            
        y = self.logposteriorratio(trypath[0], trypath[-1])
        
        for k in range(stage):
            y = y + self.qfun(k, trypath, invR)
            
        alpha = min(np.ones(1), np.exp(y)*a2*(a1**(-1)))
        
        return alpha
        
    def qfun(self, iq, trypath, invR):
        # Gaussian nth stage log proposal ratio
        # log of q_i(y_n,...,y_{n-j})/q_i(x,y_1,...,y_j)
            
        stage = len(trypath) - 1 - 1 # - 1, iq; 
        if stage == iq: # shift index due to 0-indexing
            zq = np.zeros(1) # we are symmetric
        else:
            iR = invR[iq] # proposal^(-1/2)
            y1 = trypath[0].theta
            y2 = trypath[iq + 1].theta # check index
            y3 = trypath[stage + 1].theta
            y4 = trypath[stage - iq].theta
            zq = -0.5*((np.linalg.norm(np.dot(y4-y3, iR)))**2 - (np.linalg.norm(np.dot(y2-y1, iR)))**2)
            
        return zq 
        
    def logposteriorratio(self, x1, x2):
        zq = -0.5*(sum((x2.ss*(x2.sigma2**(-1.0)) - x1.ss*(x1.sigma2**(-1.0)))) + x2.prior - x1.prior)
        return sum(zq)