National Wildlife Federation
==============================

Accessing, processing, documenting wildlife and environmental datasets for the National Wildlife Federation

### Project Description

The National Wildlife Federation (NWF) is a large non-profit dedicated to conservation and wildlife advocacy. NWF is working with another organization to create an interactive mapping tool that shows the intersection of potential carbon management project with wildlife and envirornmental considerations in the state of Wyoming. Data Clinic is tasked with finding and processing these wildlife and envirornmental datasets and providing them to NWF. NWF has given us a [spreadsheet](https://docs.google.com/spreadsheets/d/1qZX01JpzITLJDCWByWUadBp64f7d0Il5FQknywnsXpQ/edit#gid=0) outlining the desired datasets, which we have augmented with additional metadata.

The data pipeline we build will contain a few distinct steps, with each step depending on the previous. Roughly, these steps are:

1.  **Access data and upload to s3**
    - The metadata spreadsheet contains links to APIs and hosted files matching the requested datasets. The code in `download.py` should iterate through the datasets with links and download each locally before uploading to the `nwf-dataclinic` s3 bucket.
2.  **Simple data processing**
    - The raw data on s3 will have different file formats, projects, and extents. We want to provide NWF with data that has been minimally processed to ensure compatibility. The code in `process.py` should traverse the raw datasets and apply these basic processing steps and save the results to s3.
3.  **Documenting processed data**
    - The final step is to create simple documentation for each dataset. These should be pdf files generated for each processed dataset. These documents will contain information from the metadata, such as dataset description, licence, years covered, etc. as well as some additional information dervived from the data itself such as column names/types and number of rows. The code in `document.py` will iterate through the processed datasets and create the documentation for each.

These steps are composed in `run.py` - which also exports the full contents of the repository to a specified local folder.

### Environment Set-up

1.  Ensure you have a python 3.9 or higher installation on your external machine
2.  Install poetry following the instructions [here](https://python-poetry.org/docs/#installing-with-the-official-installer)
3.  From the root project directory, install the depencies with `poetry install`
4.  Ensure the envirornment has been installed by running `poetry shell`. You should see something like `(nwf-process-geodata-py3.9)` in your terminal. 

### Git stuff 

We encourage people to follow the git feature branch workflow which you can read more about here: [How to use git as a Data Scientist](https://towardsdatascience.com/why-git-and-how-to-use-git-as-a-data-scientist-4fa2d3bdc197)

For each feature you are adding to the code 

1. Switch to the main branch and pull the most recent changes 
```
git checkout main 
git pull
```

2. Make a new branch for your addition 
```
git checkout -b cleaning_script
``` 
3. Write your awesome code.
4. Once it's done add it to git 
```
git status
git add {files that have changed}
git commit -m {some descriptive commit message}
```
5. Push the branch to gitlab 
```
git push -u origin cleaning_script
``` 
6. Go to GitHub and create a merge request.
7. Either merge the branch yourself if your confident it's good or request that someone else reviews the changes and merges it in.
8. Repeat
9. ...
10. Profit.

<p><small>Project based on the <a target="_blank" href="https://drivendata.github.io/cookiecutter-data-science/">cookiecutter data science project template</a>. #cookiecutterdatascience</small></p>
