# -----------------------------------------------------------------------------
# Make copy of source code next to the metsearch script.

setenv METSEARCH_DIR scripts/metsearch

if ( -d "$METSEARCH_DIR" ) then
    rm -Rf ${METSEARCH_DIR}
endif

mkdir ${METSEARCH_DIR}
cp -r metsearch ${METSEARCH_DIR}

# -----------------------------------------------------------------------------
# Compile the app

# I don't know why, but without entering and leaving python first,
# the shell complains that pyinstaller is undefined.
./linux-venv/bin/python -c "exit()"

pyinstaller --clean --noconfirm --noconsole --onefile --add-data="metsearch/metsearch.ui:metsearch" -i icon/themet.png -p ${METSEARCH_DIR} scripts/metsearch-gui

# -----------------------------------------------------------------------------
# Remove the copy of the source code.

rm -Rf ${METSEARCH_DIR}