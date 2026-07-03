#!/bin/bash

echo "Starting precision download with error isolation..."
echo "--------------------------------------------------------"

# Create a subfolder to hold extensions that fail the version/commit checkout
FAILED_DIR="failed_checkouts"
mkdir -p "$FAILED_DIR"

# Format: "DirectoryName:VersionOrCommit:URL"
EXT_CONFIGS=(
    "ParserHooks:1.6.1:https://github.com/JeroenDeDauw/ParserHooks.git"
    "CLDR:4.10.0:https://github.com/wikimedia/mediawiki-extensions-cldr.git"
    "GetUserName:2.0:https://github.com/Wikimedica/MediaWiki-extensions-GetUserName.git"
    "Description2:0.4.1:https://github.com/wikimedia/mediawiki-extensions-Description2.git"
    "Disambiguator:1.3:https://github.com/wikimedia/mediawiki-extensions-Disambiguator.git"
    "DismissableSiteNotice:1.0.1:https://github.com/wikimedia/mediawiki-extensions-DismissableSiteNotice.git"
    "PageNotice:f84e356:https://github.com/wikimedia/mediawiki-extensions-PageNotice.git"
    "MobileFrontend:2.3.0:https://github.com/wikimedia/mediawiki-extensions-MobileFrontend.git"
    "Flow:1.2.0:https://github.com/wikimedia/mediawiki-extensions-Flow.git"
    "WikiLove:1.3.1:https://github.com/wikimedia/mediawiki-extensions-WikiLove.git"
    "Thanks:1.2.0:https://github.com/wikimedia/mediawiki-extensions-Thanks.git"
    "Matomo:4.0.0:https://github.com/DaSchTour/matomo-mediawiki-extension.git"
    "RegexFun:1.3.0:https://github.com/wikimedia/mediawiki-extensions-RegexFun.git"
    "Variables:2.5.1:https://github.com/wikimedia/mediawiki-extensions-Variables.git"
    "RandomSelection:2.3.0:https://github.com/wikimedia/mediawiki-extensions-RandomSelection.git"
    "MyVariables:3.5.1:https://github.com/wikimedia/mediawiki-extensions-MyVariables.git"
    "OpenGraphMeta:0.5.5:https://github.com/wikimedia/mediawiki-extensions-OpenGraphMeta.git"
    "MetaMaster:0.1.0:https://github.com/wikimedia/mediawiki-extensions-MetaMaster.git"
    "EmbedVideo:2.8.0:https://gitlab.com/HydraWiki/extensions/embedvideo.git"
    "RssFeed:2.25.1:https://github.com/wikimedia/mediawiki-extensions-RSS.git"
    "TemplateSandbox:1.1.0:https://github.com/wikimedia/mediawiki-extensions-TemplateSandbox.git"
    "InviteSignup:1.0.0:https://github.com/wikimedia/mediawiki-extensions-InviteSignup.git"
    "UserMerge:1.10.1:https://github.com/wikimedia/mediawiki-extensions-UserMerge.git"
    "Echo:988a9f7:https://github.com/wikimedia/mediawiki-extensions-Echo.git"
    "ContactPage:2.3:https://github.com/wikimedia/mediawiki-extensions-ContactPage.git"
    "TimeMachine:0.3:https://github.com/wikimedia/mediawiki-extensions-TimeMachine.git"
    "NewestPages:1.22:https://github.com/wikimedia/mediawiki-extensions-NewestPages.git"
    "MassEditRegex:8.4.0:https://github.com/wikimedia/mediawiki-extensions-MassEditRegex.git"
    "PagedTiffHandler:c37a325:https://github.com/wikimedia/mediawiki-extensions-PagedTiffHandler.git"
    "AbuseFilter:30dcb55:https://github.com/wikimedia/mediawiki-extensions-AbuseFilter.git"
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