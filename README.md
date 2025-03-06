Project goal: Building an AI feature on AWS from scratch

Story:
a company has a prod DB and wants to build an AI feature in his product.

Demo of how this would be done in AWS

Step 1: 
- build data pipeline to an analytics warehouse
     - tools: dlt, dbt, step function, iceberg
     - considerations: frequency, volumne, observability, data quality

Step 2:
- build an AI feature
     - tools
     - how to host it ?
     - how to monitor it ?

Step 3:
- integrate the AI prediction in the data pipeline


To do:
- 1: define dataset
    propositions: 
        list of customer reviews for a product

- 2: define the AI feature + a model
    proposition:  
        clustering of reviews into categories ?

- 3: build basic data pipeline
- 4: build basic prediction
- 5: build prediction integration in data pipeline
- 6: slides + demo
