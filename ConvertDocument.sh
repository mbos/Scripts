#!/bin/bash
# ConvertDocument.sh
# Script to convert between Microsoft Word and Markdown formats using pandoc
# Version: 0.2
# Copyright 2025 Mike Bos
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is furnished
# to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Function to handle errors
# Usage: handle_error "Primary error message" ["Detailed secondary message"]
handle_error() {
    echo "ERROR: $1" >&2
    if [[ -n "$2" ]]; then
        echo "Details: $2" >&2
    fi
    exit 1
}

# Function to display usage information
show_usage() {
    echo "Usage: $0 [options] [--] <input_file> [pandoc_options...]"
    echo "Options:"
    echo "  -o, --output <file>    Specify output file name"
    echo "  -f, --force            Force overwrite of existing output file"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Arguments:"
    echo "  <input_file>           The document to convert (e.g., .docx, .md)"
    echo "  [pandoc_options...]    Additional options passed directly to pandoc (after '--' if needed)"
    echo ""
    echo "Examples:"
    echo "  $0 document.docx                 # Convert Word to Markdown (output: document.md)"
    echo "  $0 document.md                   # Convert Markdown to Word (output: document.docx)"
    echo "  $0 -o custom.md document.docx    # Specify output filename"
    echo "  $0 -f -o existing.md document.docx # Force overwrite existing.md"
    echo "  $0 document.md -- --toc          # Convert Markdown to Word with a Table of Contents"
    echo "  $0 document.docx -- -t markdown_strict # Convert Word to strict Markdown"
    exit 0
}

# Function to check if pandoc is installed
check_pandoc() {
    command -v pandoc &> /dev/null || handle_error "Pandoc is not installed. Please install it first."
}

# Function to check if a file exists and handle overwriting
# Usage: check_file_exists "output_file_path" force_overwrite_flag
# Returns the final output path (original, user-confirmed, or auto-generated)
check_file_exists() {
    local output_file="$1"
    local force_overwrite="$2" # Should be 1 to force, 0 otherwise

    if [ -f "$output_file" ]; then
        if [[ "$force_overwrite" -eq 1 ]]; then
            echo "Overwriting existing file '$output_file' due to --force option." >&2
        else
            read -p "File '$output_file' already exists. Overwrite? (y/n): " answer
            if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
                local dir
                dir=$(dirname -- "$output_file")
                local filename
                filename=$(basename -- "$output_file")
                local base_name="${filename%.*}"
                local extension="${output_file##*.}"
                # Handle cases with no extension or dotfiles correctly
                if [[ "$filename" == "$extension" ]] || [[ "$filename" == ".$extension" ]]; then
                    extension="" # No extension or starts with dot
                else
                    extension=".$extension"
                fi

                local counter=1
                local new_output_file
                while : ; do
                    new_output_file="${dir}/${base_name}_${counter}${extension}"
                    [ ! -f "$new_output_file" ] && break
                    ((counter++))
                done
                output_file="$new_output_file"
                echo "Using new filename: $output_file" >&2
            fi
        fi
    fi
    echo "$output_file"
}

# Helper function to resolve paths and generate output filenames
# Usage: resolve_output_file "input_file" "output_arg" "default_extension" force_overwrite_flag
# Returns the final, absolute output path after checking existence
resolve_output_file() {
    local input_file="$1"
    local output_arg="$2"
    local default_extension="$3"
    local force_overwrite="$4" # 1 for true, 0 for false

    # Use realpath if available, otherwise fallback (basic check)
    local resolved_input_file
    if command -v realpath &> /dev/null; then
        resolved_input_file=$(realpath "$input_file")
    else
        # Basic fallback: if it doesn't start with /, prepend pwd
        if [[ "$input_file" != /* ]]; then
            resolved_input_file="$PWD/$input_file"
        else
            resolved_input_file="$input_file"
        fi
        # Note: This fallback doesn't resolve symlinks or '..'
    fi

    local output_file
    local input_dir
    input_dir=$(dirname -- "$resolved_input_file")

    if [ -z "$output_arg" ]; then
        # Generate default output filename
        local input_basename
        input_basename=$(basename -- "$resolved_input_file")
        local base_name="${input_basename%.*}"
        output_file="${input_dir}/${base_name}.${default_extension}"
    else
        # Use provided output filename
        # Resolve relative to input dir if not absolute
        if [[ "$output_arg" != /* ]]; then
            output_file="${input_dir}/${output_arg}"
        else
            output_file="$output_arg"
        fi
        # Use realpath for the output too, if available, for consistency
        if command -v realpath &> /dev/null; then
             # Use realpath -m to handle non-existent paths for creation
            output_file=$(realpath -m "$output_file")
        fi
    fi

    # Check existence and handle overwrite/rename
    echo "$(check_file_exists "$output_file" "$force_overwrite")"
}

# Function to run pandoc and handle errors
# Usage: run_pandoc "input" "output" "pandoc_options_array..."
run_pandoc() {
    local input_file="$1"
    local output_file="$2"
    shift 2
    local pandoc_opts=("$@") # Capture remaining args as pandoc options

    echo "Converting '$input_file' to '$output_file'..." >&2
    echo "Pandoc command: pandoc -s \"$input_file\" -o \"$output_file\" ${pandoc_opts[*]}" >&2

    # Execute pandoc, capturing stderr
    local pandoc_stderr
    if ! pandoc_stderr=$(pandoc -s "$input_file" -o "$output_file" "${pandoc_opts[@]}" 2>&1); then
        handle_error "Pandoc conversion failed." "$pandoc_stderr"
    fi
    echo "Conversion successful: '$output_file'"
}

# Function to convert Word to Markdown
# Usage: word_to_markdown "input" "output_arg" force_flag "pandoc_options_array..."
word_to_markdown() {
    local input_file="$1"
    local output_arg="$2"
    local force_flag="$3"
    shift 3
    local pandoc_opts=("$@")
    local output_file
    output_file=$(resolve_output_file "$input_file" "$output_arg" "md" "$force_flag")
    run_pandoc "$input_file" "$output_file" "${pandoc_opts[@]}"
}

# Function to convert Markdown to Word
# Usage: markdown_to_word "input" "output_arg" force_flag "pandoc_options_array..."
markdown_to_word() {
    local input_file="$1"
    local output_arg="$2"
    local force_flag="$3"
    shift 3
    local pandoc_opts=("$@")
    local output_file
    output_file=$(resolve_output_file "$input_file" "$output_arg" "docx" "$force_flag")
    run_pandoc "$input_file" "$output_file" "${pandoc_opts[@]}"
}

# --- Define global variables for options ---
output_file=""
force_overwrite=0 # 0 = false, 1 = true
input_file=""
pandoc_opts=()

# --- Replacement for getopt parsing ---
parse_options() {
    # Note: This function modifies the global variables defined above.
    local -a remaining_args=() # Use local array for temporary storage

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -o|--output)
                if [[ -z "$2" || "$2" == -* ]]; then
                    handle_error "Option '$1' requires an argument."
                fi
                output_file="$2" # Modifies global
                shift 2
                ;;
            -f|--force)
                force_overwrite=1 # Modifies global
                shift
                ;;
            -h|--help)
                show_usage # Exits
                ;;
            --)
                shift # Consume '--'
                remaining_args+=("$@") # All subsequent args are non-options
                break
                ;;
            -*)
                handle_error "Unknown option: $1"
                ;;
            *)
                # First non-option argument is the input file
                if [[ -z "$input_file" ]]; then
                    input_file="$1" # Modifies global
                else
                    # Subsequent non-option arguments are pandoc options
                    remaining_args+=("$1")
                fi
                shift
                ;;
        esac
    done

    # Assign remaining args to pandoc_opts (modifies global)
    if [[ ${#remaining_args[@]} -gt 0 ]]; then
         pandoc_opts=("${remaining_args[@]}")
    fi

    # Validation after parsing
    if [[ -z "$input_file" ]]; then
        handle_error "No input file specified. Use -h for help."
    fi
}

# Main function
main() {
    check_pandoc

    # Parse options using the manual function - modifies globals
    parse_options "$@"

    # Validate input file existence (uses the global input_file)
    # Use a temporary variable to avoid modifying input_file before resolve_output_file needs it
    local check_input="$input_file"
     if [[ "$check_input" != /* ]]; then
        check_input="$PWD/$check_input" # Make absolute for check
    fi
    if [[ ! -f "$check_input" ]]; then
         # Try realpath if available for a better check
         if command -v realpath &> /dev/null; then
             check_input=$(realpath "$input_file" 2>/dev/null) || : # Ignore error if it doesn't exist
         fi
         if [[ ! -f "$check_input" ]]; then
            handle_error "Input file '$input_file' does not exist or is not a regular file."
         fi
         # If realpath found it, update input_file for consistency (optional)
         # input_file="$check_input"
    fi


    # Determine conversion direction based on input file extension
    local extension
    # Use parameter expansion for robustness
    extension="${input_file##*.}"
    # Convert to lowercase if not empty
    [[ -n "$extension" ]] && extension=$(echo "$extension" | tr '[:upper:]' '[:lower:]')

    case "$extension" in
        docx|doc|odt)
            word_to_markdown "$input_file" "$output_file" "$force_overwrite" "${pandoc_opts[@]}"
            ;;
        md|markdown|txt)
            markdown_to_word "$input_file" "$output_file" "$force_overwrite" "${pandoc_opts[@]}"
            ;;
        *)
            # Removed unreliable is_markdown detection
            handle_error "Cannot determine conversion direction: Unknown or missing extension for '$input_file'. Please use a standard extension (.docx, .doc, .odt, .md, .markdown, .txt)."
            ;;
    esac
}

# Run the main function
main "$@"
