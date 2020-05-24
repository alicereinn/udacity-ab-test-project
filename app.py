import math
import pandas as pd
from scipy import stats
import streamlit as st

st.title("Udacity A/B Testing Final Project")

"""
I recently completed Google and Udacity's introduction to A/B testing, which was pretty interesting! This is my take on the final project. 
The problem definition below comes almost verbatim from the instructions found [here](https://docs.google.com/document/u/1/d/1aCquhIqsUApgsxQ8-SQBAigFDcfWVVohLEXcV6jWbdI/pub?embedded=True).

*At the time of this experiment, Udacity courses currently have two options on the course overview page: "start free trial", and "access course materials". 
If the student clicks "start free trial", they will be asked to enter their credit card information, and then they will be enrolled in a free trial 
for the paid version of the course. After 14 days, they will automatically be charged unless they cancel first. If the student clicks 
"access course materials", they will be able to view the videos and take the quizzes for free, but they will not receive coaching support 
or a verified certificate, and they will not submit their final project for feedback.*

*In the experiment, Udacity tested a change where if the student clicked "start free trial", they were asked how much time they had available 
to devote to the course. If the student indicated 5 or more hours per week, they would be taken through the checkout process as usual. 
If they indicated fewer than 5 hours per week, a message would appear indicating that Udacity courses usually require a greater time commitment 
for successful completion, and suggesting that the student might like to access the course materials for free. At this point, 
the student would have the option to continue enrolling in the free trial, or access the course materials for free instead. 
The screenshot below shows what the experiment looks like.*
"""
from PIL import Image

image = Image.open("screenshot.png")
st.image(image, caption="The experimental pop-up", use_column_width=True)
"""
*The hypothesis was that this might set clearer expectations for students upfront, thus reducing the number of frustrated students who left the free trial 
because they didn't have enough time—without significantly reducing the number of students to continue past the free trial and eventually 
complete the course. If this hypothesis held true, Udacity could improve the overall student experience and improve coaches' capacity to support students 
who are likely to complete the course.*

*The unit of diversion is a cookie, although if the student enrolls in the free trial, they are tracked by user-id from that point forward. 
The same user-id cannot enroll in the free trial twice. For users that do not enroll, their user-id is not tracked in the experiment, 
even if they were signed in when they visited the course overview page.*

## Metric choice
As evaluation metrics, I chose:
* Gross conversion, that is number of users to enroll in the free trial divided by number of users to click on "start free trial" ($d_{min}=0.01$)
* Net conversion, that is number of users to make at least one payment divided by number of users to click on "start free trial"  ($d_{min}=0.0075$)

If the experiment has an effect, then we would expect gross conversion to decrease, and hope for net conversion not to significantly decrease.

The invariant metrics I used are:
* Number of cookies visiting the course overview page
* Number of clicks on the “start free trial” button

This makes sense because all of these activities occur before the user is even shown the modified page, 
which is only shown after the button is clicked. Therefore, any change in these metrics after the experiments should be treated as suspicious, 
and investigated further. 

## Measuring variability
The next step is estimating the baseline variability of each evaluation metric. This allows us to later calculate a suitable sample size for
the experiment, and verify that the experiment is feasible.  Below are the rough estimates of the baseline values for each metric.
"""

baseline_values = pd.read_csv("baseline.csv", names=["Metric", "Value"])
baseline_values

r"""
I use pageviews from here onwards as short-hand for the number of unique cookies viewing the course overview page 
(in the given data, it shows as cookies).
The exercise calls for making an analytical estimate of the standard deviation based on a $N_{pageviews}=5000$.
However, for both metrics,
the standard deviation is based on the number of users who clicked the "start free trial" button, not the number of pageviews.
The above data allows us to estimate this number for our given sample size, knowing the proportion of people who do click the button.
The resulting standard deviations are shown in the following table.
"""

n = 5000

sd_gross_conversion = math.sqrt(
    (baseline_values.loc[4, "Value"] * (1 - baseline_values.loc[4, "Value"]))
    / (n * (baseline_values.loc[3, "Value"]))
)

sd_net_conversion = math.sqrt(
    (baseline_values.loc[6, "Value"] * (1 - baseline_values.loc[6, "Value"]))
    / (n * (baseline_values.loc[3, "Value"]))
)

sd_all = pd.DataFrame(
    [[sd_gross_conversion, sd_net_conversion]],
    columns=["Sd. Gross conversion", "Sd. Net conversion"],
)
sd_all

"""
Since both metrics are probabilities, they should approximately follow a binomial distribution.
Because of this, I would say we can expect the analytical estimates to be accurate.
There should be no need to try and collect empirical estimates for either.
"""

r"""
## Experiment sizing
### Sample size
The sample size is calculated on a metric-wise basis with the help of Evan Miller's 
[sample size calculator](https://www.evanmiller.org/ab-testing/sample-size.html), which I have reimplemented here.
Since we have two evaluation metrics, we use the maximum of the two calculated sample sizes as the final sample size, 
in order to ensure enough power for each metric.
We also need to keep in mind that the sample sizes we calculated refer to number of clicks needed, and needs to be converted to a sample size in pageviews.
With this in mind the results are given below.

The significance level and power used are standard picks, with $\alpha=.05$ and $\beta=.2$.
"""
from sample_size import sample_size

alpha = 0.05
beta = 0.2

d_min_gross_diff = 0.01
d_min_net_diff = 0.0075

gross_sample_size = (
    sample_size(
        alpha, 1 - beta, baseline_values.loc[4, "Value"], d_min_gross_diff,
    )
    * 2
    / baseline_values.loc[3, "Value"]
)

net_sample_size = (
    sample_size(
        alpha, 1 - beta, baseline_values.loc[6, "Value"], d_min_net_diff,
    )
    * 2
    / baseline_values.loc[3, "Value"]
)

# Index: metric columns: d_min, sample size
sample_sizes = pd.DataFrame(
    [
        [
            baseline_values.loc[4, "Value"],
            d_min_gross_diff,
            gross_sample_size,
        ],
        [baseline_values.loc[6, "Value"], d_min_net_diff, net_sample_size],
    ],
    columns=["Baseline value", "Minimum detectable difference", "Sample size"],
    index=["Gross conversion", "Net conversion"],
)
sample_sizes

total_sample_size = math.ceil(max(gross_sample_size, net_sample_size))

"""
The resulting sample size is $N_{pageviews}=""" + str(
    total_sample_size
) + """$. Due to implementation difference this number differs slightly from the original sample size calculator."""

experiment_duration = math.ceil(
    total_sample_size / baseline_values.loc[0, "Value"]
)

"""
### Duration vs. exposure

I decided to run the experiment on 100% of traffic, for a couple of reasons:
* No other running or anticipated future test is mentioned in the project instructions, so I assumed there would be enough bandwidth 
for full traffic to be split 50/50.
* The potential harm in showing the feature to many users even if it ends up being taken away is very low.

The main disadvantage I identified for this approach is that there might be a bug in the feature that makes it harder for users to actually
complete their enrollment. However, this risk seemed minor, considering the feature is simply a pop-up.
A possible approach would be to run a smaller test on a tiny group of users beforehand,
just to make sure the feature works as expected before rolling it out to a larger experimental group.

When running the experiment on all traffic, the duration comes down to $n_{days}=""" + str(
    experiment_duration
) + """$.
Since this time interval covers at least two weekends, we can expect the results not to be significantly biased by weekly seasonalities.

## Analysis
After running the mock experiment for the chosen number of days, we can analyze the results.
The first step, before we evaluate the significance of the results, is running sanity checks on the invariant metrics.
If, and only if, the sanity checks pass, we calculate statistical and practical significance, and run a sign test for additional confirmation.

**Note:** This is where the calculations started getting confusing for me, and perhaps for you too, if you are working on the project yourself. 
First, In the Excel file we are given, enrollments and payments are missing after November 2 for some reason. 
Moreover, the results Udacity expects you to find are not related to how many days your decided to run your experiment.
How many days you have to include (if you want your calculations to be marked as correct) even varies between the sanity checks and the effect size and sign 
test calculations, which I found strange. 
I consider the correct calculations to be based on the $n_{days}$ I calculated, so you will see my numbers based on that.
However, if you adjust the number of days on the slider, you can match Udacity's results. The tables will update immediately.
"""
max_days = len(pd.read_csv("control.csv"))
number_of_days = st.slider(
    label="Number of days to run the experiment",
    min_value=1,
    max_value=max_days,
    value=experiment_duration,
)

control_data = pd.read_csv("control.csv")[:number_of_days]

"""
Below are the results for the control group.
"""
control_data

experiment_data = pd.read_csv("experiment.csv")[:number_of_days]

"""
And those for the experiment group.
"""
experiment_data


"""
### Sanity checks
The sanity checks involve comparing the control and experiment groups to ensure no unexpected differences arose during the experiment, 
for instance due to technical issue or faulty group assignment.
Specifically, we check that the total pageviews and clicks were successfully assigned to each group with a 50/50 split.
Below is the aggregated data from the final results.

(The slider should be on 37 days for the results to match Udacity's.)
"""

# Control
enrollments_cont = control_data["Enrollments"].sum()

clicks_cont = control_data["Clicks"].sum()

pageviews_cont = control_data["Pageviews"].sum()

payments_cont = control_data["Payments"].sum()

gross_conversion_cont = enrollments_cont / clicks_cont
net_conversion_cont = payments_cont / clicks_cont


# Experiment
enrollments_exp = experiment_data["Enrollments"].sum()

clicks_exp = experiment_data["Clicks"].sum()

pageviews_exp = experiment_data["Pageviews"].sum()

payments_exp = experiment_data["Payments"].sum()

gross_conversion_exp = enrollments_exp / clicks_exp
net_conversion_exp = payments_exp / clicks_exp

raw_data = [
    [pageviews_cont, clicks_cont, enrollments_cont, payments_cont],
    [pageviews_exp, clicks_exp, enrollments_exp, payments_exp],
]

# Calculate totals
raw_data.append([sum(x) for x in zip(raw_data[0], raw_data[1])])

aggregated_data = pd.DataFrame(
    raw_data,
    columns=["Cookies", "Clicks", "Enrollments", "Payments"],
    index=["Control", "Experiment", "Total"],
)
aggregated_data

cookies_control = aggregated_data.loc["Control", "Cookies"]
cookies_experiment = aggregated_data.loc["Experiment", "Cookies"]

clicks_control = aggregated_data.loc["Control", "Clicks"]
clicks_experiment = aggregated_data.loc["Experiment", "Clicks"]


# Proportion of cookies in control
cookies_control_proportion = cookies_control / (
    cookies_control + cookies_experiment
)
m_cookies = stats.norm.ppf(1 - alpha / 2) * math.sqrt(
    0.5 ** 2 / (cookies_control + cookies_experiment)
)
ci_cookies_low = 0.5 - m_cookies
ci_cookies_high = 0.5 + m_cookies


# Proportion of clicks in control
# (probability that a click ends up in control)
clicks_control_proportion = clicks_control / (
    clicks_control + clicks_experiment
)
m_clicks = stats.norm.ppf(1 - alpha / 2) * math.sqrt(
    0.5 ** 2 / (clicks_control + clicks_experiment)
)
ci_clicks_low = 0.5 - m_clicks
ci_clicks_high = 0.5 + m_clicks

if (
    cookies_control_proportion > ci_cookies_low
    and cookies_control_proportion < ci_cookies_high
):
    cookies_sanity_pass = "yes"
else:
    cookies_sanity_pass = "no"

if (
    clicks_control_proportion > ci_clicks_low
    and clicks_control_proportion < ci_clicks_high
):
    clicks_sanity_pass = "yes"
else:
    clicks_sanity_pass = "no"

sanity_intervals = pd.DataFrame(
    [
        [
            ci_cookies_low,
            ci_cookies_high,
            cookies_control_proportion,
            cookies_sanity_pass,
        ],
        [
            ci_clicks_low,
            ci_clicks_high,
            clicks_control_proportion,
            clicks_sanity_pass,
        ],
    ],
    columns=["Lower bound", "Upper bound", "Observed", "Passes"],
    index=["Cookies", "Clicks"],
)
sanity_intervals


"""
Both invariant metrics pass the sanity check. This confirms that the experiment was set up and run correctly, and that we can trust the results.

### Practical and statistical significance

The conversion values for both groups, together with the respective confidence interval calculated around them, are shown below.
I decided not to use the Bonferroni correction as the evaluation metrics are correlated (since they represent different "levels" of the same funnel),
and therefore the method might prove too conservative and make it harder to detect a change.

(The slider should be on 23 days to match Udacity's results.)
"""

conversion_data = [
    [gross_conversion_cont, net_conversion_cont],
    [gross_conversion_exp, net_conversion_exp],
]

# Create the pandas DataFrame
conversions = pd.DataFrame(
    conversion_data,
    columns=["Gross conversion", "Net conversion"],
    index=["Control", "Experiment"],
)
conversions

pooled_probability_gross_conversion = (enrollments_cont + enrollments_exp) / (
    clicks_cont + clicks_exp
)

pooled_probability_net_conversion = (payments_cont + payments_exp) / (
    clicks_cont + clicks_exp
)

alpha = 0.05
critical_two_tailed = stats.norm.ppf(1 - alpha / 2)

pooled_se_gross_conversion = math.sqrt(
    pooled_probability_gross_conversion
    * (1 - pooled_probability_gross_conversion)
    * (1 / clicks_cont + 1 / clicks_exp)
)
margin_gross = critical_two_tailed * pooled_se_gross_conversion

pooled_se_net_conversion = math.sqrt(
    pooled_probability_net_conversion
    * (1 - pooled_probability_net_conversion)
    * (1 / clicks_cont + 1 / clicks_exp)
)
margin_net = critical_two_tailed * pooled_se_net_conversion

# initialize list of lists
gross_diff = gross_conversion_exp - gross_conversion_cont
net_diff = net_conversion_exp - net_conversion_cont

if margin_gross < abs(gross_diff):
    gross_stat_signif = "yes"
else:
    gross_stat_signif = "no"

if d_min_gross_diff < min(
    abs(gross_diff - margin_gross), abs(gross_diff + margin_gross)
):
    gross_pract_signif = "yes"
else:
    gross_pract_signif = "no"


if margin_net < abs(net_diff):
    net_stat_signif = "yes"
else:
    net_stat_signif = "no"

if d_min_net_diff < min(
    abs(net_diff - margin_net), abs(net_diff + margin_net)
):
    net_pract_signif = "yes"
else:
    net_pract_signif = "no"

ci_data = [
    [
        gross_diff,
        gross_diff - margin_gross,
        gross_diff + margin_gross,
        gross_stat_signif,
        gross_pract_signif,
    ],
    [
        net_diff,
        net_diff - margin_net,
        net_diff + margin_net,
        net_stat_signif,
        net_pract_signif,
    ],
]

# Create the pandas DataFrame
confidence_intervals = pd.DataFrame(
    ci_data,
    columns=["Difference", "Lower bound", "Upper bound", "S.", "P.",],
    index=["Gross conversion", "Net conversion"],
)
confidence_intervals

"""
Gross conversion shows a decrease that is both statistically and practically significant.
Net conversion also decreased, but not by a practically significant amount.

### Sign tests
To additionally validate our results, we can perform a sign test comparing the two groups on each day of the experiment.
For each day the experiment was run, we consider the difference between the metric values for experiment and control.
For the gross conversion, we expect the difference between the experiment and control values to be negative on most days.
Conversely, we expect the differences to be more or less evenly split between positive and negative for net conversion,
since this is the metric we expected to not significantly move.
"""

gross_conversion_diff = (
    experiment_data["Enrollments"] / experiment_data["Clicks"]
    - control_data["Enrollments"] / control_data["Clicks"]
)
net_conversion_diff = (
    experiment_data["Payments"] / experiment_data["Clicks"]
    - control_data["Payments"] / control_data["Clicks"]
)
daily_differences = pd.DataFrame(
    {
        "Date": control_data["Date"],
        "Δ Gross conversion": gross_conversion_diff,
        "Δ Net conversion": net_conversion_diff,
    }
)
daily_differences

p_value_sign_gross = stats.binom_test(
    x=sum(x > 0 for x in gross_conversion_diff), n=number_of_days
)
p_value_sign_net = stats.binom_test(
    x=sum(x > 0 for x in net_conversion_diff), n=number_of_days
)
p_values_data = [p_value_sign_gross, p_value_sign_net]

p_values = pd.DataFrame(
    {
        "P-value": p_values_data,
        "Significant": ["yes" if x < alpha else "no" for x in p_values_data],
    },
    index=["Gross conversion", "Net conversion"],
)
p_values

"""
Gross conversion shows a statistically significant difference, which is in agreement with the evaluation based on the confidence interval.
However, this is not the case for net conversion, which shows a statistically significant difference based on the confidence interval,
but not based on the sign test.
Looking again at the confidence interval, we can see that the upper bound is negative, but close to zero.
In the sign test, even if the p-value is quite high, most days have a negative difference,
which matches the information we get from confidence interval.

### Recommendation

Both confidence interval and the sign test for gross conversion showed that the metric decreased significantly, as hypothesized.
However, the two tests did not agree on net conversion, that according to the confidence interval went down in a statistically significant way
(which is undesirable), but not according to the sign test. 
However, the confidence interval also tells us that net conversion did not decrease in a practically significant way.
Because of this, my recommendation would be to launch the feature for everyone.

## Follow-up experiment
### How to reduce early cancellations?
We have already seen that one way of reducing the number of frustrated student who cancel their trial early is to discourage these students from
entering the trial altogether, if they are not able to put in the time, which was the focus of the experiment.
However, there might still be students who might make a good time commitment, and put a reasonable effort in the course, 
only to get frustrated with their lack of progress at a later point. This can happen if the student picked a course that he or she did not
have the appropriate prerequisites for, or if the course is perceived to be too hard. The student is then much more likely to cancel early.

An interesting approach could involve tracking metrics related to how long students actively spend on each lesson or section of a course, 
that is watching lessons or attempting exercises. 
If their learning is progressing slowly, it might help to allow them to switch to the trial version of a more appropriate course,
to make it more likely that they will continue after the end of their trial.
For instance, students could get an email inviting them to switch to one of the prerequisite courses, if they have not taken it yet.
There are some drawbacks, however. 
Some students might have specific learning habits that are causing slow progress, even though are not actually experiencing difficulties.
On the other hand, even if these students got an email about a course change, 
they might simply choose to ignore it, without impacting their likelihood of cancellation.
Another issue is that there might not always be a prerequisite course to switch to, or a similar but easier course to suggest.
In this case, it is probably enough to simply not send any email at all to frustrated students in the experiment group,
and just allow them to continue the course as if they were in the control. 
This would still generate useful information on how much impact the new feature can have.

The unit of diversion would be an user-id, since the experiment involves users that are already registered to the site, albeit not paying.
To decide if someone in the experiment group should be suggested another course, I would calculate these metrics for each user,
after they have spent some predetermined X hours on a course (may be a different amount depending on each course):
* Ratio of total time spent watching video lectures relative to the number of lectures watched
* Average number of attempts per exercise

We are only interested in knowing if fewer users will cancel early, or in other words, we want to know whether more users make at least a payment.
Both retention and net conversion are good candidates. 
However, net conversion would allow us to draw a conclusion with far fewer samples, therefore this is the metric I would recommend using.
For the experiment to be a success, we should see net conversion increasing significantly.
Otherwise, the changes should not be rolled out to everyone.
"""
