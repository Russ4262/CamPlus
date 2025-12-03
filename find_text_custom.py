# coding=utf-8
#!/usr/bin/python

__author__ = "Russell Johnson"
__doc__ = "Command line script designed to be placed in the parent install folder of a release build of FreeCAD for Windows. \
The script attempts to identify and remove debug files within the release build, trimming the overall size of the install directory."


import os

CWD = os.getcwd()


def search_files(files, text):
    results = []
    for f in files:
        with open(f, "r") as fp:
            lines = fp.readlines()
            i = 0
            nums = []
            for ln in lines:
                i += 1
                if ln.find(text) != -1:
                    nums.append(i)
            if nums:
                results.append((f, nums))
    return results


def identify_python_files(file_names_list):
    python_files = []
    for filename in file_names_list:
        parts = filename.split(".")
        extension = parts.pop()
        name = ".".join(parts)
        if extension == "py":
            python_files.append(name + "." + extension)
    return python_files


def scan_directory(parent):
    print(f"Scanning:: {parent}")
    search_candidates = []
    count = 1

    # Cycle through input directory recursively with config.os.walk()
    for dir_path, dir_list, file_names_list in os.walk(parent):
        # print(f"dir_path: {dir_path}")
        candidates = identify_python_files(file_names_list)

        if candidates:
            # print(f"dir_path: {dir_path}")
            # print(f"   ... {len(candidates)} files identified")
            for f in candidates:
                search_candidates.append(dir_path + "\\" + f)
        count += 1
    # Efor

    search_candidates.sort(reverse=True)

    print(f"{len(search_candidates)} total files identified")

    return search_candidates


def print_contents(results):
    for f, nums in results:
        print(f)
        with open(f, "r") as fp:
            lines = fp.readlines()
            i = 0
            for ln in lines:
                i += 1
                if i in nums:
                    print(f"     {i} :: {ln[:-1]}")


print("Executing find_text script ...")

search = True
while search:
    text = input("Enter string to find: ")

    files = scan_directory(CWD)
    results = search_files(files, text)
    print(f"Results found in {len(results)} files.")

    yn = input("Print line contents? (Y,N): ")
    if yn == "Y" or yn == "y":
        print_contents(results)
    else:
        sm = input("Print summary? (Y,N): ")
        if sm == "Y" or sm == "y":
            for f, l in results:
                print(f"{f} :: {len(l)} instances")

    s = input("\n\nSearch again? (Y,N): ")
    if s != "Y" and s != "y":
        search = False
        break
