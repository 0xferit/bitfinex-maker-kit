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
        
        # Check if it's a direct push or fast-forward merge (single parent)
        if [[ "$parent_count" -eq 1 ]]; then
            # For fast-forward merges, check the commit messages to determine source
            # Look at recent commits to find merge base and branch info
            source_branch=""
            
            # Check the last 10 commits for branch information
            recent_commits=$(git log --format="%H %s" -n 10 "$newrev")
            while IFS= read -r commit_line; do
                commit_msg="${commit_line#* }"
                # Check for branch indicators in commit messages
                if [[ "$commit_msg" =~ \[develop\] ]] || [[ "$commit_msg" =~ from[[:space:]]develop ]]; then
                    source_branch="develop"
                    break
                elif [[ "$commit_msg" =~ \[release/([^]]+)\] ]] || [[ "$commit_msg" =~ from[[:space:]]release/([^[:space:]]+) ]]; then
                    source_branch="release/${BASH_REMATCH[1]}"
                    break
                fi
            done <<< "$recent_commits"
            
            # If we can't determine source, check if it's a fast-forward from develop/release
            if [[ -z "$source_branch" ]]; then
                # Check if the new commits are reachable from develop or release branches
                if git merge-base --is-ancestor "$newrev" origin/develop 2>/dev/null; then
                    source_branch="develop"
                else
                    # Check release branches
                    for ref in $(git for-each-ref --format='%(refname:short)' refs/remotes/origin/release/); do
                        if git merge-base --is-ancestor "$newrev" "$ref" 2>/dev/null; then
                            source_branch="${ref#origin/}"
                            break
                        fi
                    done
                fi
            fi
            
            # If still no source found, it's likely a direct push
            if [[ -z "$source_branch" ]]; then
                echo "❌ Rejected: Direct pushes to main are not allowed"
                echo "   Please create a PR from develop or release/* branch"
                exit 1
            fi
            
            # Validate source branch
            if [[ "$source_branch" != "develop" ]] && [[ ! "$source_branch" =~ ^release/ ]]; then
                echo "❌ Rejected: Only 'develop' or 'release/*' branches can be merged to main"
                echo "   Detected source: $source_branch"
                exit 1
            fi
            
        # If it's a merge commit (has 2 parents)
        elif [[ "$parent_count" -eq 2 ]]; then
            # Get merge commit message to detect source branch
            merge_msg=$(git log --format=%s -n 1 "$newrev")
            
            # Try to extract branch name from merge message
            # Standard GitHub/GitLab merge message format: "Merge pull request #X from org/branch"
            # or "Merge branch 'branch' into main"
            source_branch=""
            
            if [[ "$merge_msg" =~ Merge[[:space:]]pull[[:space:]]request[[:space:]]#[0-9]+[[:space:]]from[[:space:]]([^[:space:]]+) ]]; then
                # GitHub PR format - extract full branch path
                full_branch="${BASH_REMATCH[1]}"
                # Only remove org/ prefix, preserve release/ or other prefixes
                if [[ "$full_branch" =~ ^[^/]+/(.+)$ ]]; then
                    source_branch="${BASH_REMATCH[1]}"
                else
                    source_branch="$full_branch"
                fi
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
            # More than 2 parents (octopus merge) or no parents
            echo "❌ Rejected: Unusual merge detected (parent count: $parent_count)"
            echo "   Please use standard merge from develop or release/* branch"
            exit 1
        fi
    fi
done

exit 0