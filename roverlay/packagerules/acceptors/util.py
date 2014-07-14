# R overlay -- package rules, utility functions for acceptors
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

# Functions that return package info values
# * accessing p_info._info directly here

DEFAULT_CATEGORY_REPLACEMENT = '@default'


def get_repo_name ( p_info ):
   return p_info._info ['repo_name']
# --- end of get_repo_name (...) ---

def get_package ( p_info ):
   # package name with version
   return p_info._info ['package_filename_x']
# --- end of get_package (...) ---

def get_package_name ( p_info ):
   return p_info._info ['package_name']
# --- end of get_package_name (...) ---

def get_ebuild_name ( p_info ):
   return p_info ['name']
# --- end of get_ebuild_name (...) ---

def get_category ( p_info ):
   return p_info.get ( 'category', None ) or DEFAULT_CATEGORY_REPLACEMENT
# --- end of get_category (...) ---
