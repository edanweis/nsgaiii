# -*- coding: utf-8 -*-
import time, array, random, copy, math
from itertools import chain
from operator import attrgetter, itemgetter
from scipy.special import expit

import matplotlib as mpl
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d as a3
from matplotlib.path import Path
import matplotlib.patches as patches
import numpy as np

from deap import algorithms, base, benchmarks, tools, creator
from nsgaiii import *
import pprint as pp
import pandas as pd
from collector import collect_variables


creator.create("FitnessMin3", base.Fitness, weights=(-1.0,) * 3)
creator.create("Individual3", array.array, typecode='d', 
							 fitness=creator.FitnessMin3)


# data = pd.read_csv('test.csv', header=None, index_col=0).itertuples()
# print(pd.read_csv('test.csv', header=None, index_col=0))


i = {".key": 1, "place": 2, "event": 3, "active": 4, "open_now": 5, "open_time": 6, "close_time": 7, "maximum_visit_duration": 8, "minimum_visit_duration": 9, "travel_time": 10, "travel_distance": 11, "travel_mode": 12, "rainfall": 13, "sunset": 14, "weather_score": 15, "weather_dependent": 16, "suitable_for_weather_score": 17, "average_social_rating": 18, "number_reviews": 19, "suitable_for_children": 20, "suitable_for_groups": 21, "suitable_for_vision_impaired": 22, "suitable_for_bicycles": 23, "suitable_for_wheelchair": 24, "eat": 25, "see": 26, "do": 27, "popularity_now": 28, "popularity_avg_current_day": 29, "popularity_avg_current_hour": 30, "better_when": 31, "elevation": 32, "bicycle_duration":33, "bicycle_distance": 34, "operated_by": 35 }

def get_data():	
	return data.next()

def product_no_repeats(*args):
	for p in itertools.product(*args):
		if len(set(p)) == len(p):
			yield p

def reservoir(it, k):
	ls = [next(it) for _ in range(k)]
	for i, x in enumerate(it, k + 1):
		j = random.randint(0, i)
		if j < k:
			ls[j] = x
	return ls


def generate_random_tuples_norepeat(size, range_min, range_max):
	xs = range(range_min, range_max)
	ys = range(range_min, range_max)
	zs = range(range_min, range_max)
	return reservoir(product_no_repeats(xs, ys, zs), size)

def evaluate_activity(individual):
	# CONVENIENCE: sufficient time, weather, proximity, elevation, 
	# print("social rating: %s" % individual[18])
	# ( (0.1 * No reviews ) * avg_social_rating) * (0.1 if operated_by == council) * (1 + travel distance if travel mode = car) * (eat see or do > 0)

	desirability = 1 - (individual[i['average_social_rating']]/5.00)
	convenience = 1 - expit(individual[i['travel_time']])
	elevation = 1 - expit(individual[i['elevation']])
	print desirability, convenience, elevation

	# return [random.uniform(0,1), random.uniform(0,1), random.uniform(0,1)]
	return [desirability, convenience, elevation]
	# return [random.uniform()]
	# return 


def prepare_toolbox(problem_instance, selection_func, number_of_variables, bounds_low, bounds_up):
		def uniform(low, up, size=None):
				try:
					# print [random.uniform(a, b) for a, b in zip(low, up)]
					return [random.uniform(a, b) for a, b in zip(low, up)]
					# return [0.23, 0.532,0.143, 0.53,0.265, 0.523,0.2787, 0.5343,0.243, 0.567,0.12, 0.598,0.12, 0.875,0.76, 0.67,0.9, 0.9,0.54, 0.23,0.2235, 0.543],[0.344, 0.322,0.453, 0.3,0.65, 0.2,0.987, 0.743,0.343, 0.367,0.02, 0.298,0.52, 0.475,0.16, 0.27,0.1, 0.3,0.4, 0.3,0.35, 0.43]
					# return [0.23, 0.532,0.143, 0.53,0.265, 0.523,0.2787, 0.5343,0.243, 0.567,0.12, 0.598,0.12, 0.875,0.76, 0.67,0.9, 0.9,0.54, 0.23,0.2235, 0.543],[0.344, 0.322,0.453, 0.3,0.65, 0.2,0.987, 0.743,0.343, 0.367,0.02, 0.298,0.52, 0.475,0.16, 0.27,0.1, 0.3,0.4, 0.3,0.35, 0.43]
				except TypeError:
					return [0.23, 0.532] #, 0.143, 0.53, 0.265, 0.523, 0.2787, 0.5343, 0.243, 0.567, 0.12, 0.598, 0.12, 0.875, 0.76, 0.67, 0.9, 0.9, 0.54, 0.23, 0.2235, 0.543], [0.344, 0.322, 0.453, 0.3, 0.65, 0.2, 0.987, 0.743, 0.343, 0.367, 0.02, 0.298, 0.52, 0.475, 0.16, 0.27, 0.1, 0.3, 0.4, 0.3, 0.35, 0.43]
					# print "type error" 
					# [random.uniform(a, b) for a, b in zip([low] * size, [up] * size)]
					# return [random.uniform(a, b) for a, b in zip([low] * size, [up] * size)]
		
		toolbox = base.Toolbox()
		toolbox.register('evaluate', problem_instance)
		toolbox.register('select', selection_func)
		toolbox.register("attr_float", get_data)
		toolbox.register("individual", tools.initIterate, creator.Individual3, toolbox.attr_float)
		toolbox.register("population", tools.initRepeat, list, toolbox.individual)
		# toolbox.register("population_guess", initPopulation, list, creator.Individual, "my_guess.json")

		toolbox.register("mate", tools.cxSimulatedBinaryBounded,
										 low=bounds_low, up=bounds_up, eta=20.0)
		toolbox.register("mutate", tools.mutPolynomialBounded,
										 low=bounds_low, up=bounds_up, eta=20.0,
										 indpb=1.0/number_of_variables)
		toolbox.pop_size = 30   # population size
		toolbox.max_gen = 80    # max number of iteration
		toolbox.mut_prob = 1 / number_of_variables
		toolbox.cross_prob = 0 # trouble here
		return toolbox

number_of_variables = 34
bounds_low, bounds_up = 0, 1

def dtlz2(individual, obj):
	"""DTLZ2 multiobjective function. It returns a tuple of *obj* values. 
	The individual must have at least *obj* elements.
	From: K. Deb, L. Thiele, M. Laumanns and E. Zitzler. Scalable Multi-Objective 
	Optimization Test Problems. CEC 2002, p. 825 - 830, IEEE Press, 2002.
	"""
	xc = individual[:obj-1]
	xm = individual[obj-1:]
	g = sum((xi-0.5)**2 for xi in xm)
	f = [(1.0+g) *  reduce(mul, (cos(0.5*xi*pi) for xi in xc), 1.0)]
	f.extend((1.0+g) * reduce(mul, (cos(0.5*xi*pi) for xi in xc[:m]), 1) * sin(0.5*xc[m]*pi) for m in range(obj-2, -1, -1))
	print(f)
	return f

def nsga_iii(toolbox, stats=None, verbose=False):
		population = toolbox.population(n=toolbox.pop_size)
		return algorithms.eaMuPlusLambda(population, toolbox,
			mu=toolbox.pop_size, 
			lambda_=toolbox.pop_size, 
			cxpb=toolbox.cross_prob, 
			mutpb=toolbox.mut_prob,
			ngen=toolbox.max_gen,
			stats=stats, verbose=verbose)


def plot():
	fig = plt.figure(figsize=(7,7))
	ax = fig.add_subplot(111, projection='3d')
	for ind in res:
			ax.scatter(ind.fitness.values[0],
								 ind.fitness.values[1],
								 ind.fitness.values[2],
								 c='purple', marker='o')
	ax.set_xlabel('$f_1()$', fontsize=15)
	ax.set_ylabel('$f_2()$', fontsize=15)
	ax.set_zlabel('$f_3()$', fontsize=15)
	ax.view_init(elev=11, azim=-21)
	plt.autoscale(tight=True)
	plt.show()




def main():
	toolbox = prepare_toolbox(problem_instance=evaluate_activity, selection_func=sel_nsga_iii, number_of_variables=number_of_variables, bounds_low=bounds_low, bounds_up=bounds_up)

	# print(toolbox.individual())
	# pp.pprint(toolbox.population(n=2))

	stats = tools.Statistics()
	stats.register('pop', copy.deepcopy)
	res, logbook = nsga_iii(toolbox, stats=stats)

	# best = tools.selBest(res, 1)
	# print(best)
	fig = plt.figure(figsize=(7,7))
	ax = fig.add_subplot(111, projection='3d')
	for ind in res:
			ax.scatter(ind.fitness.values[0],
								 ind.fitness.values[1],
								 ind.fitness.values[2],
								 c='purple', marker='o')
	ax.set_xlabel('$f_1()$', fontsize=15)
	ax.set_ylabel('$f_2()$', fontsize=15)
	ax.set_zlabel('$f_3()$', fontsize=15)
	ax.view_init(elev=11, azim=-21)
	plt.autoscale(tight=True)
	plt.show()

	# plot()

if __name__ == "__main__":
	data = collect_variables(start=0, end=571, save=True, floats_only=True, caching=False)
	# main()