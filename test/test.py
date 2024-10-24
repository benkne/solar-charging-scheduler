import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

# # Data
# timestamps = [-23400.0, -22500.0, -21600.0, -20700.0, -19800.0, -18900.0, -18000.0, -17100.0, -16200.0, -15300.0, -14400.0, -13500.0, -12600.0, -11700.0, -10800.0, -9900.0, -9000.0, -8100.0, -7200.0, -6300.0, -5400.0, -4500.0, -3600.0, -2700.0, -1800.0, -900.0, 0.0, 900.0, 1800.0, 2700.0, 3600.0, 4500.0, 5400.0, 6300.0, 7200.0, 8100.0, 9000.0, 9900.0, 10800.0, 11700.0, 12600.0, 13500.0, 14400.0, 15300.0, 16200.0, 17100.0, 18000.0, 18900.0, 19800.0, 20700.0, 21600.0, 22500.0]
# values = [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.03053435114503817,0.08142493638676844,0.09923664122137406,0.12213740458015268,0.15267175572519087,0.19338422391857507,0.24173027989821885,0.2926208651399491,0.35114503816793896,0.40966921119592875,0.4758269720101781,0.544529262086514,0.6106870229007635,0.6717557251908398,0.7353689567430025,0.8040712468193385,0.8625954198473282,0.905852417302799,0.9338422391857508,0.9567430025445293,0.9770992366412214,0.9923664122137404,1.0,0.9923664122137404,0.9770992366412214,0.9516539440203562,0.916030534351145,0.8702290076335878,0.8117048346055981,0.7404580152671755,0.6641221374045803,0.5877862595419847,0.5165394402035624,0.450381679389313,0.38676844783715014,0.32824427480916035,0.272264631043257,0.22137404580152673,0.178117048346056,0.14503816793893132,0.12213740458015268,0.043256997455470736,0.0050890585241730275,0.0]

# # Scale down timestamps
# timestamps = np.divide(timestamps, 100)

# values = np.multiply(values,100)

# timestamps = timestamps[20:-10]
# values = values[20:-10]

def quad(x, a, b, c):
    return a * x**2 + b * x + c

def line(a,b,x):
    return a*x+b

def gauss(x,a,mu,sigma):
    return a * np.exp(-(x - mu)**2 / (2 * sigma**2))

# # Updated initial guess for [b, a, mu, sigma]
# initial_guess = [0,0]

# # Perform curve fitting
# params, covariance = curve_fit(line, 
#                                 timestamps,
#                                 values, 
#                                 p0=initial_guess,
#                                 bounds = ([-100,-100], [100,100]))

# a_fit, b_fit = params
# print("Fitted parameters:", params)
# print("Covariance matrix:")
# print(covariance)

# # Plot the fit and the original data
# plt.plot(timestamps, [line(a_fit, b_fit, x) for x in timestamps], label="Fitted Gaussian")
# plt.plot(timestamps, values, 'o', label="Original Data")

# plt.ylim(-1,110)

# plt.legend()
# plt.show()










timestamps = [-23400.0, -22500.0, -21600.0, -20700.0, -19800.0, -18900.0, -18000.0, -17100.0, -16200.0, -15300.0, -14400.0, -13500.0, -12600.0, -11700.0, -10800.0, -9900.0, -9000.0, -8100.0, -7200.0, -6300.0, -5400.0, -4500.0, -3600.0, -2700.0, -1800.0, -900.0, 0.0, 900.0, 1800.0, 2700.0, 3600.0, 4500.0, 5400.0, 6300.0, 7200.0, 8100.0, 9000.0, 9900.0, 10800.0, 11700.0, 12600.0, 13500.0, 14400.0, 15300.0, 16200.0, 17100.0, 18000.0, 18900.0, 19800.0, 20700.0, 21600.0, 22500.0]
values = [0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.03053435114503817,0.08142493638676844,0.09923664122137406,0.12213740458015268,0.15267175572519087,0.19338422391857507,0.24173027989821885,0.2926208651399491,0.35114503816793896,0.40966921119592875,0.4758269720101781,0.544529262086514,0.6106870229007635,0.6717557251908398,0.7353689567430025,0.8040712468193385,0.8625954198473282,0.905852417302799,0.9338422391857508,0.9567430025445293,0.9770992366412214,0.9923664122137404,1.0,0.9923664122137404,0.9770992366412214,0.9516539440203562,0.916030534351145,0.8702290076335878,0.8117048346055981,0.7404580152671755,0.6641221374045803,0.5877862595419847,0.5165394402035624,0.450381679389313,0.38676844783715014,0.32824427480916035,0.272264631043257,0.22137404580152673,0.178117048346056,0.14503816793893132,0.12213740458015268,0.043256997455470736,0.0050890585241730275,0.0]

# Scale down timestamps
timestamps = np.divide(timestamps, 100)

x = timestamps
y = values

initial_guess = [1, 0, 100]

params, covariance = curve_fit(gauss, x, y, p0=initial_guess)

a_fit, b_fit, c_fit = params

print(covariance)
print(params)

plt.plot(x, y, 'o', color ='red', label ="data")

fitted_values = gauss(timestamps, a_fit, b_fit, c_fit)
plt.plot(timestamps, fitted_values, label='Fitted Quadratic', color='red')

#plt.ylim(0,10)
#plt.xlim(-10,10)

plt.legend()
plt.show()


# import numpy as np
# import matplotlib.pyplot as plt
# from scipy.optimize import curve_fit

# # Step 1: Define the quadratic function
# def quad(x, a, b, c):
#     return a * x**2 + b * x + c

# # Example data (replace with your actual data)
# timestamps = np.array([0, 1, 2, 3, 4, 5])
# values = np.array([5, 4, 6, 7, 10, 12])

# # Step 2: Perform curve fitting
# # Initial guess for parameters [a, b, c]
# initial_guess = [1, 1, 1]

# # Fit the quadratic curve to the data
# params, covariance = curve_fit(quad, timestamps, values, p0=initial_guess)

# # Extract fitted parameters a, b, and c
# a_fit, b_fit, c_fit = params
# print("Fitted parameters:")
# print("a =", a_fit, ", b =", b_fit, ", c =", c_fit)
# print("Covariance matrix:")
# print(covariance)

# # Step 3: Plot the data and the fitted curve
# # Original data
# plt.plot(timestamps, values, 'o', label='Original Data')

# # Fitted quadratic curve
# fitted_values = quad(timestamps, a_fit, b_fit, c_fit)
# plt.plot(timestamps, fitted_values, label='Fitted Quadratic', color='red')

# # Add labels and legend
# plt.xlabel('Timestamps')
# plt.ylabel('Values')
# plt.legend()

# # Show the plot
# plt.show()
