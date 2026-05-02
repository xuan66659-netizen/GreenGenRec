# Data Analysis Report

This report summarizes the exploratory data analysis for the GreenGenRec project.

## 1. Dataset Files

- RAW_recipes.csv: `D:\GreenGenRec\data\raw\RAW_recipes.csv`
- RAW_interactions.csv: `D:\GreenGenRec\data\raw\RAW_interactions.csv`
- Carbon reference CSV: `D:\GreenGenRec\data\external\food-emissions-supply-chain.csv`

## 2. Basic Dataset Information

| dataset                     |    rows |   columns | column_names                                                                                                           |
|:----------------------------|--------:|----------:|:-----------------------------------------------------------------------------------------------------------------------|
| RAW_recipes                 |  231637 |        12 | name, id, minutes, contributor_id, submitted, tags, nutrition, n_steps, steps, description, ingredients, n_ingredients |
| RAW_interactions            | 1132367 |         5 | user_id, recipe_id, date, rating, review                                                                               |
| food_emissions_supply_chain |      43 |        10 | Entity, Year, Land use change, Farm, Animal feed, Processing, Transport, Retail, Packaging, Losses                     |

## 3. Recipe Data Summary

| metric                         |        value |
|:-------------------------------|-------------:|
| recipe_rows                    | 231637       |
| unique_recipe_id               | 231637       |
| duplicated_recipe_id           |      0       |
| missing_name_count             |      1       |
| recipes_with_empty_ingredients |      0       |
| avg_ingredient_count           |      9.05115 |
| median_ingredient_count        |      9       |
| recipes_with_empty_tags        |    109       |
| minutes_missing_count          |      0       |
| minutes_mean                   |   9398.55    |
| minutes_median                 |     40       |
| minutes_99_percentile          |    903.92    |

## 4. Nutrition Summary

| nutrition_field   |   missing_count |   missing_rate |     mean |   median |       std |   min |   p01 |   p25 |   p50 |   p75 |     p99 |    max |
|:------------------|----------------:|---------------:|---------:|---------:|----------:|------:|------:|------:|------:|------:|--------:|-------:|
| calories          |               0 |              0 | 473.942  |    313.4 | 1189.71   |     0 |  18.4 | 174.4 | 313.4 | 519.7 | 3516.96 | 434360 |
| total_fat         |               0 |              0 |  36.0807 |     20   |   77.7988 |     0 |   0   |   8   |  20   |  41   |  302    |  17183 |
| sugar             |               0 |              0 |  84.2969 |     25   |  800.081  |     0 |   0   |   9   |  25   |  68   | 1141.64 | 362729 |
| sodium            |               0 |              0 |  30.1475 |     14   |  131.962  |     0 |   0   |   5   |  14   |  33   |  219    |  29338 |
| protein           |               0 |              0 |  34.6819 |     18   |   58.4725 |     0 |   0   |   7   |  18   |  51   |  188    |   6552 |
| saturated_fat     |               0 |              0 |  45.5892 |     23   |   98.2358 |     0 |   0   |   7   |  23   |  52   |  404    |  10395 |
| carbohydrates     |               0 |              0 |  15.5604 |      9   |   81.8246 |     0 |   0   |   4   |   9   |  16   |  154    |  36098 |

## 5. Interaction Data Summary

| metric                            | value             |
|:----------------------------------|:------------------|
| interaction_rows                  | 1132367           |
| unique_users                      | 226570            |
| unique_interacted_recipes         | 231637            |
| rating_missing_count              | 0                 |
| rating_mean                       | 4.411016039852804 |
| positive_interactions_rating_ge_4 | 1003724           |
| positive_interaction_ratio        | 0.886394605282563 |
| date_missing_or_invalid_count     | 0                 |
| min_date                          | 2000-01-25        |
| max_date                          | 2018-12-20        |

## 6. Carbon Reference Summary

| metric                   | value                                                                                              |
|:-------------------------|:---------------------------------------------------------------------------------------------------|
| carbon_reference_rows    | 43                                                                                                 |
| carbon_reference_columns | 10                                                                                                 |
| column_names             | Entity, Year, Land use change, Farm, Animal feed, Processing, Transport, Retail, Packaging, Losses |

## 7. Carbon Keyword Coverage in Food.com

| carbon_category   |   recipe_count |   recipe_ratio | keywords                                                                             |
|:------------------|---------------:|---------------:|:-------------------------------------------------------------------------------------|
| vegetables        |         136514 |     0.589345   | tomato, onion, carrot, spinach, broccoli, mushroom, lettuce, cabbage, pepper, potato |
| rice_pasta        |          92932 |     0.401197   | rice, pasta, noodle, noodles, bread, flour                                           |
| egg               |          62813 |     0.27117    | egg, eggs                                                                            |
| fruit             |          61256 |     0.264448   | apple, banana, orange, lemon, berry, strawberry, blueberry                           |
| cheese            |          60980 |     0.263257   | cheese, cheddar, mozzarella, parmesan, cream cheese                                  |
| chicken           |          39801 |     0.171825   | chicken, turkey, poultry                                                             |
| pork              |          30150 |     0.130161   | pork, bacon, ham, sausage, pepperoni                                                 |
| tofu_beans        |          22286 |     0.0962109  | tofu, beans, bean, lentils, lentil, chickpea, peas                                   |
| beef              |          20766 |     0.0896489  | beef, steak, ground beef, sirloin                                                    |
| fish              |          11933 |     0.0515159  | fish, salmon, tuna, cod, shrimp                                                      |
| lamb              |           1580 |     0.00682102 | lamb, mutton                                                                         |

## 8. Notes for Later Preprocessing

- Rating >= 4 can be used as positive feedback.
- User/item k-core filtering should be considered because recommendation data is usually sparse and long-tailed.
- Nutrition fields should be clipped before normalization because outliers may exist.
- Carbon labels should be treated as weak labels, not exact life-cycle carbon emissions.
- Recipe text can be built from name, ingredients, tags, nutrition buckets, and carbon level.
