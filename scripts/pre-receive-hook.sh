#!/bin/bash
# Git pre-receive hook to enforce branch flow
# Install this on your Git server in: hooks/pre-receive
set -euo pipefail

while read oldrev newrev refname; do
    # Validate input
    if [[ -z "${newrev:-}" ]] || [[ -z "${refname:-}" ]]; then
        echo "❌ Error: Invalid input received"
        exit 1
    fi
    
    # Check for deleted branch (all-zero SHA)
    if [[ "$newrev" =~ ^0+$ ]]; then
        # Branch deletion is allowed
        continue
    fi
    
    # Check if pushing to main
    if [[ "$refname" == "refs/heads/main" ]]; then
        # Validate that newrev is a valid commit
        if ! git rev-parse --verify "$newrev" >/dev/null 2>&1; then
            echo "❌ Error: Invalid commit SHA: $newrev"
            exit 1
        fi
        
        # Get the commit details
        merge_commit=$(git rev-parse "$newrev")
        parents=$(git show --format=%P -s "$merge_commit")
        parent_count=$(echo "$parents" | wc -w)
        
        # If it's a merge commit (has 2 parents)
        if [[ "$parent_count" -eq 2 ]]; then
            # Get merge commit message to detect source branch
            merge_msg=$(git log --format=%s -n 1 "$newrev")
            
            # Try to extract branch name from merge message
            # Standard GitHub/GitLab merge message format: "Merge pull request #X from org/branch"
            # or "Merge branch 'branch' into main"
            source_branch=""
            
            if [[ "$merge_msg" =~ Merge[[:space:]]pull[[:space:]]request[[:space:]]#[0-9]+[[:space:]]from[[:space:]]([^[:space:]]+) ]]; then
                # GitHub PR format
                source_branch="${BASH_REMATCH[1]}"
                # Remove org prefix if present
                source_branch="${source_branch##*/}"
            elif [[ "$merge_msg" =~ Merge[[:space:]]branch[[:space:]][\'\"]([^\'\"]+)[\'\"] ]]; then
                # Standard git merge format
                source_branch="${BASH_REMATCH[1]}"
            fi
            
            # If we couldn't detect from merge message, deny for safety
            if [[ -z "$source_branch" ]]; then
                echo "❌ Rejected: Could not determine source branch"
                echo "   Please ensure you're merging from develop or release/* branch"
                exit 1
            fi
            
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