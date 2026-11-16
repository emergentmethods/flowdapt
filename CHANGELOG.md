
<a name="0.1.54"></a>
## [0.1.54](https://gitlab.com/emergentmethods/flowdapt/compare/0.1.53...0.1.54)

> 2026-11-16

### Fix

* Full docker build and ensure runtime_env works with ray 2.60.0


<a name="0.1.53"></a>
## [0.1.53](https://gitlab.com/emergentmethods/flowdapt/compare/0.1.52...0.1.53)

> 2026-11-14

### Fix

* Bump python on all stages
* Bump python
* Address memory leak, bump Ray to v2.60.0


<a name="0.1.52"></a>
## [0.1.52](https://gitlab.com/emergentmethods/flowdapt/compare/0.1.51...0.1.52)

> 2026-06-13

### Fix

* Cache stages without the resource definitions, only check physical resources, let Ray handle logical resources


<a name="0.1.51"></a>
## [0.1.51](https://gitlab.com/emergentmethods/flowdapt/compare/0.1.50...0.1.51)

> 2026-06-07

### Fix

* Give config option for force reaping idle Ray workers


<a name="0.1.50"></a>
## [0.1.50](https://gitlab.com/emergentmethods/flowdapt/compare/0.1.49...0.1.50)

> 2026-06-05

### Fix

* Ensure mapper is unique per plugin to help blue/green drain cycles


<a name="0.1.49"></a>
## [0.1.49](https://gitlab.com/emergentmethods/flowdapt/compare/0.1.48...0.1.49)

> 2026-06-05

### Fix

* Tests
* Add a drain mechanism, and cache ray remote functions to avoid memory leak


<a name="0.1.48"></a>
## [0.1.48](https://gitlab.com/emergentmethods/flowdapt/compare/0.1.47...0.1.48)

> 2026-05-31

### Fix

* Add allow_partial_failure to parameterized stages


<a name="0.1.47"></a>
## [0.1.47](https://gitlab.com/emergentmethods/flowdapt/compare/0.1.46...0.1.47)

> 2026-05-24

### Fix

* Avoid blocking calls


<a name="0.1.46"></a>
## 0.1.46

> 2026-05-24

### Fix

* Move node check out of the environmnet_info()

