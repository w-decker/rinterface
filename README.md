# rinterface
_Quickly interface with R in Python._

Have you ever needed to run some R code in-between some Python code? Do you want to avoid figuring out [`rpy2`](https://rpy2.github.io/)? Then check out `RInterface`!

## Installation 

```bash
pip install git+https://github.com/w-decker/rinterface.git
```

## `rinterface()`
A single, all-purpose function for quickly interfacing with R in Python.
### Basic
At its most basic implementation `rinterface()` takes in a "script" of R-valid code, generates a temporary file (`"temp.R"`), evaluates the script using the `Rscript` command-line tool and then deletes the temporary file. Below is a basic example with the corresponding output.

```python
import rinterface.rinterface as R

code = """
data(iris)
model <- model <- lm(Sepal.Length ~ Sepal.Width + Petal.Length + Petal.Width, data=iris)
summary(model)
"""

# execute your R script
R(code)
```
```plain
Call:
lm(formula = Sepal.Length ~ Sepal.Width + Petal.Length + Petal.Width, 
    data = iris)

Residuals:
     Min       1Q   Median       3Q      Max 
-0.82816 -0.21989  0.01875  0.19709  0.84570 

Coefficients:
             Estimate Std. Error t value Pr(>|t|)    
(Intercept)   1.85600    0.25078   7.401 9.85e-12 ***
Sepal.Width   0.65084    0.06665   9.765  < 2e-16 ***
Petal.Length  0.70913    0.05672  12.502  < 2e-16 ***
Petal.Width  -0.55648    0.12755  -4.363 2.41e-05 ***
---
Signif. codes:  0 ‘***’ 0.001 ‘**’ 0.01 ‘*’ 0.05 ‘.’ 0.1 ‘ ’ 1

Residual standard error: 0.3145 on 146 degrees of freedom
Multiple R-squared:  0.8586,	Adjusted R-squared:  0.8557 
F-statistic: 295.5 on 3 and 146 DF,  p-value: < 2.2e-16
```

You can also save your script too.

```python
R(code, save=True, fname="my_script.R")
```

## Capturing output

You can also "capture" the output from your R script. This returns the output as a formatted string.

```python
import rinterface.rinterface as R

code = """
data(iris)

model <- lm(Sepal.Length ~ Sepal.Width + Petal.Length + Petal.Width, data=iris)
summary(model)
"""
# execute your R script
output = R(code, capture=True)
print(output.stdout)
```
```plain
Call:
lm(formula = Sepal.Length ~ Sepal.Width + Petal.Length + Petal.Width, 
    data = iris)

Residuals:
     Min       1Q   Median       3Q      Max 
-0.82816 -0.21989  0.01875  0.19709  0.84570 

Coefficients:
             Estimate Std. Error t value Pr(>|t|)    
(Intercept)   1.85600    0.25078   7.401 9.85e-12 ***
Sepal.Width   0.65084    0.06665   9.765  < 2e-16 ***
Petal.Length  0.70913    0.05672  12.502  < 2e-16 ***
Petal.Width  -0.55648    0.12755  -4.363 2.41e-05 ***
---
Signif. codes:  0 ‘***’ 0.001 ‘**’ 0.01 ‘*’ 0.05 ‘.’ 0.1 ‘ ’ 1

Residual standard error: 0.3145 on 146 degrees of freedom
Multiple R-squared:  0.8586,	Adjusted R-squared:  0.8557 
F-statistic: 295.5 on 3 and 146 DF,  p-value: < 2.2e-16
```

## Grabbing variables

Although seeing the output of your R script in your IPython environment is convienent, it is limiting. Sometimes you might need to access the values generated in your R script. You can access these values using a simple heuristic: `# @grab{type}`. Here's how to do it: 1) assign the value you want to a variable. 2) On the line above this variable, write the "tag": `# @grab{type}` and input the type (e.g., `str`, `int`, `float`, etc.) that you wish to load in the variable as. 

>[!IMPORTANT]
>The tag must be on the immediate line before the variable you wish to grab, and there must be an empty line below that variable before any new code can written.

```python
import rinterface.rinterface as R

code = """
data(iris)

model <- lm(Sepal.Length ~ Sepal.Width + Petal.Length + Petal.Width, data=iris)

# @grab{float}
aic <- AIC(model)

# @grab{float}
bic <- BIC(model)
"""
# execute your R script
aic, bic = R(code, grab=True)
aic, bic
```
```plain
(84.64272, 99.6959)
```

### More on grabbing

Thus far, the grabbing procedure can access arrays, matrices, integers, floats and strings in R and can load them back into Python as `int, float, str, list[int], list[float], list[str], pandas.DataFrame` or `np.ndarray`. 

```python
import rinterface.rinterface as R

code = """
# @grab{np.ndarray}
M <- matrix(1:6, 2, 3)

# @grab{list[float]}
y <- c(43.55, 3.0342, 3.23432)

# @grab{list[int]}
v <- c(10, 20, 30)

df <- data.frame(
  colA = c(1.5, 2.5, 3.5),
  colB = c(10, 20, 30),
  colC = c(100, 200, 300)
)

# @grab{pd.DataFrame}
df
"""
# execute your R script
results = R(code, grab=True)
print(results[0], type(results[0]))  
print(results[1], type(results[1]))  
print(results[2], type(results[2])) 
print(results[3], type(results[3]))
```
```plain
[[1. 2. 3.]
 [4. 5. 6.]] <class 'numpy.ndarray'>
[43.55, 3.0342, 3.23432] <class 'list'>
[10, 20, 30] <class 'list'>
   colA  colB   colC
0   1.5  10.0  100.0
1   2.5  20.0  200.0
2   3.5  30.0  300.0 <class 'pandas.core.frame.DataFrame'>
```

>[!WARNING]
>Grabbing is great, but it has _not_ been thoroughly tested. Edge cases are bound to arise. Scalar values, strings and R's `data.frame` are the safest types in R to convert to equivalent types in Python.

>[!TIP]
>If you're having trouble grabbing certain variables, here are a few suggestions: 1) write a print statement and capture the output (`R(code, capture=True)`). 2) Just grab the variable as a string and manipulate it yourself.

## Some interface helpers
Floats, and integers are easy to integrate from your Python environment into your `rinterface.rinterface` script:

```python 
import rinterface.rinterface as R

x = 10

code = f"""
print({x})
"""

# execute your R script
R(code)
```
```plain
[1] 10
```

However, things like numpy arrays and pandas dataframes are more difficult. Enter `rinterface.utils`. With one simple function (`to_r()`), you can integrate your numpy arrays and pandas dataframes right into your R code at runtime. 

```python
import rinterface.rinterface as R
from rinterface.utils import to_r

from sklearn.datasets import load_iris
iris = load_iris()
iris = pd.DataFrame(iris.data, columns=iris.feature_names)

code = f"""
df <- {to_r(iris)}
head(df)
"""

# execute your R script
R(code)
```
```plain
  sepal.length..cm. sepal.width..cm. petal.length..cm. petal.width..cm.
1               5.1              3.5               1.4              0.2
2               4.9              3.0               1.4              0.2
3               4.7              3.2               1.3              0.2
4               4.6              3.1               1.5              0.2
5               5.0              3.6               1.4              0.2
6               5.4              3.9               1.7              0.4
```
`rinterface.utils.to_r()` supports Python types `str`, `bool`, `np.ndarray` and `pd.DataFrame`

>[!WARNING]
>`rinterface.utils` has _not_ been thoroughly tested. Edge cases and errors are bound to arise.