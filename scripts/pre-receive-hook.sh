#!/bin/bash
# Git pre-receive hook to enforce branch flow
# Install this on your Git server in: hooks/pre-receive

while read oldrev newrev refname; do
    # Check if pushing to main
    if [[ "$refname" == "refs/heads/main" ]]; then
        # Get the branch being merged
        merge_commit=$(git rev-parse $newrev)
        parents=$(git show --format=%P -s $merge_commit)
        
        # If it's a merge commit (has 2 parents)
        if [[ $(echo $parents | wc -w) -eq 2 ]]; then
            # Get the source branch
            source_commit=$(echo $parents | cut -d' ' -f2)
            source_branch=$(git branch --contains $source_commit | grep -v main | head -1 | sed 's/^[ *]*//')
            
            # Check if source is develop or release/*
            if [[ "$source_branch" != "develop" ]] && [[ ! "$source_branch" =~ ^release/ ]]; then
                echo "❌ Rejected: Only 'develop' or 'release/*' branches can be merged to main"
                echo "   Attempted merge from: $source_branch"
                exit 1
            fi
        else
            # Direct push to main (not a merge)
            echo "❌ Rejected: Direct pushes to main are not allowed"
            echo "   Please create a PR from develop or release/* branch"
            exit 1
        fi
    fi
done

exit 0