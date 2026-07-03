#!/bin/bash

echo "Starting precision download with error isolation..."
echo "--------------------------------------------------------"

# Create a subfolder to hold extensions that fail the version/commit checkout
FAILED_DIR="failed_checkouts"
mkdir -p "$FAILED_DIR"

# Format: "DirectoryName:VersionOrCommit:URL"
# NOTE: Most Wikimedia extensions use the REL1_39 branch for MW 1.39 compatibility.
# Non-Wikimedia extensions use specific release tags.
# EmbedVideo uses the old GitLab repo (2.8.0) because the new StarCitizenWiki repo
# requires PHP >= 8.0 which is incompatible with MW 1.39 on PHP 7.4.
EXT_CONFIGS=(
    "CLDR:REL1_39:https://github.com/wikimedia/mediawiki-extensions-cldr.git"
    "GetUserName:v2.1:https://github.com/Wikimedica/MediaWiki-extensions-GetUserName.git"
    "Description2:REL1_39:https://github.com/wikimedia/mediawiki-extensions-Description2.git"
    "Disambiguator:REL1_39:https://github.com/wikimedia/mediawiki-extensions-Disambiguator.git"
    "DismissableSiteNotice:REL1_39:https://github.com/wikimedia/mediawiki-extensions-DismissableSiteNotice.git"
    "PageNotice:REL1_39:https://github.com/wikimedia/mediawiki-extensions-PageNotice.git"
    "MobileFrontend:REL1_39:https://github.com/wikimedia/mediawiki-extensions-MobileFrontend.git"
    "Flow:REL1_39:https://github.com/wikimedia/mediawiki-extensions-Flow.git"
    "WikiLove:REL1_39:https://github.com/wikimedia/mediawiki-extensions-WikiLove.git"
    "Thanks:REL1_39:https://github.com/wikimedia/mediawiki-extensions-Thanks.git"
    "Matomo:v5.0.0:https://github.com/DaSchTour/matomo-mediawiki-extension.git"
    "RegexFun:REL1_39:https://github.com/wikimedia/mediawiki-extensions-RegexFun.git"
    "Variables:REL1_39:https://github.com/wikimedia/mediawiki-extensions-Variables.git"
    "RandomSelection:REL1_39:https://github.com/wikimedia/mediawiki-extensions-RandomSelection.git"
    "MyVariables:REL1_39:https://github.com/wikimedia/mediawiki-extensions-MyVariables.git"
    "OpenGraphMeta:REL1_39:https://github.com/wikimedia/mediawiki-extensions-OpenGraphMeta.git"
    "MetaMaster:REL1_39:https://github.com/wikimedia/mediawiki-extensions-MetaMaster.git"
    "EmbedVideo:2.8.0:https://gitlab.com/HydraWiki/extensions/embedvideo.git"
    "RssFeed:REL1_39:https://github.com/wikimedia/mediawiki-extensions-RSS.git"
    "TemplateSandbox:REL1_39:https://github.com/wikimedia/mediawiki-extensions-TemplateSandbox.git"
    "InviteSignup:REL1_39:https://github.com/wikimedia/mediawiki-extensions-InviteSignup.git"
    "UserMerge:REL1_39:https://github.com/wikimedia/mediawiki-extensions-UserMerge.git"
    "Echo:REL1_39:https://gerrit.wikimedia.org/r/mediawiki/extensions/Echo"
    "ContactPage:REL1_39:https://github.com/wikimedia/mediawiki-extensions-ContactPage.git"
    "TimeMachine:REL1_39:https://github.com/wikimedia/mediawiki-extensions-TimeMachine.git"
    "NewestPages:REL1_39:https://github.com/wikimedia/mediawiki-extensions-NewestPages.git"
    "MassEditRegex:REL1_39:https://github.com/wikimedia/mediawiki-extensions-MassEditRegex.git"
    "PagedTiffHandler:REL1_39:https://github.com/wikimedia/mediawiki-extensions-PagedTiffHandler.git"
    "DiscussionTools:REL1_39:https://github.com/wikimedia/mediawiki-extensions-DiscussionTools.git"
    "Linter:REL1_39:https://github.com/wikimedia/mediawiki-extensions-Linter.git"
)

for config in "${EXT_CONFIGS[@]}"; do
    ext="${config%%:*}"
    rest="${config#*:}"
    target="${rest%%:*}"
    repo_url="${rest#*:}"

    echo "Downloading $ext..."
    git clone "$repo_url" "$ext"
    
    if [ -d "$ext" ]; then
        cd "$ext" || exit
        echo "Forcing checkout state to: $target"
        
        # Track if the checkout succeeds
        CHECKOUT_SUCCESS=0

        # Try exact target first
        git checkout "$target" &> /dev/null
        if [ $? -eq 0 ]; then
            CHECKOUT_SUCCESS=1
        else
            # Try with 'v' prefix fallback
            git checkout "v$target" &> /dev/null
            if [ $? -eq 0 ]; then
                CHECKOUT_SUCCESS=1
            fi
        fi
        
        cd .. # Exit extension directory
        
        if [ $CHECKOUT_SUCCESS -eq 1 ]; then
            echo "✅ $ext locked to target version."
        else
            echo "⚠️ Warning: Could not find exact tag/commit '$target' for $ext."
            echo "📁 Moving $ext to $FAILED_DIR/ for manual handling..."
            mv "$ext" "$FAILED_DIR/"
        fi
    else
        echo "❌ Error: Failed to clone repository for $ext from $repo_url"
    fi
    echo "----------------------------------------"
done

echo "Process completed. Check the '$FAILED_DIR' folder for any mismatches."
