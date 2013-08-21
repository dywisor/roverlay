# R overlay -- stats collection, "rate" stats ("good","bad",...)
# -*- coding: utf-8 -*-
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.

import collections

import roverlay.util.objects

# 'pc' := package count(er), 'ec' := ebuild _
#
NUMSTATS = collections.OrderedDict ((
   ( 'pc_repo',          "package files found in the repositories" ),
   ( 'pc_distmap',       "package files in the mirror directory" ),
   ( 'pc_filtered',      "packages ignored by package rules" ),
   ( 'pc_queued',        "packages queued for ebuild creation" ),
   ( 'pc_success',       "packages for which ebuild creation succeeded" ),
   ( 'pc_fail',          "packages for which ebuild creation failed" ),
   # actually, it's not the package that "fails"
   ( 'pc_fail_empty',    "packages failed due to empty/unsuitable DESCRIPTION" ),
   ( 'pc_fail_dep',      "packages failed due to unresolvable dependencies" ),
   ( 'pc_fail_selfdep',  "packages failed due to unsatisfiable selfdeps" ),
   ( 'pc_fail_err',      "packages failed due to unknown errors" ),
   ( 'ec_pre',           "ebuild count prior to overlay creation" ),
   ( 'ec_post',          "ebuild count after overlay creation" ),
   ( 'ec_written',       "ebuilds written" ),
   ( 'ec_revbump',       "ebuilds rev-bumped due to package file content change" ),
))


TIMESTATS = {}

class StatsRating ( object ):

   STATUS_NONE     = 0
   ##STATUS_OK       = 2**1
   STATUS_OK       = STATUS_NONE
   STATUS_WARN     = 2**2
   STATUS_ERR      = 2**3
   STATUS_CRIT     = 2**4
   STATUS_TOO_HIGH = 2**5
   STATUS_TOO_LOW  = 2**6
   STATUS_UNDEF    = 2**7


   STATUS_WARN_LOW  = STATUS_WARN | STATUS_TOO_LOW
   STATUS_WARN_HIGH = STATUS_WARN | STATUS_TOO_HIGH
   STATUS_ERR_LOW   = STATUS_ERR  | STATUS_TOO_LOW
   STATUS_ERR_HIGH  = STATUS_ERR  | STATUS_TOO_HIGH
   STATUS_CRIT_LOW  = STATUS_CRIT | STATUS_TOO_LOW
   STATUS_CRIT_HIGH = STATUS_CRIT | STATUS_TOO_HIGH

   STATUS_ISSUES    = STATUS_WARN | STATUS_ERR | STATUS_CRIT

   STATUS_FAIL = ( ( 2**8 ) - 1 ) ^ STATUS_OK


   def __init__ ( self, description ):
      super ( StatsRating, self ).__init__()
      self.description = description
   # --- end of __init__ (...) ---

   @roverlay.util.objects.abstractmethod
   def get_rating ( self, value ):
      return STATUS_NONE
   # --- end of get_rating (...) ---

# --- end of StatsRating ---

class NumStatsCounterRating ( StatsRating ):

   def __init__ ( self, description, value,
      warn_high=None, err_high=None, crit_high=None,
      warn_low=0, err_low=0, crit_low=0
   ):
      super ( NumStatsCounterRating, self ).__init__ ( description )
      self.warn_high = warn_high
      self.err_high  = err_high
      self.crit_high = crit_high
      self.warn_low  = warn_low
      self.err_low   = err_low
      self.crit_low  = crit_low
      self.value     = value
      self.status    = self.get_rating ( value )
   # --- end of __init__ (...) ---

   @classmethod
   def new_fail_counter ( cls, description, value, warn=1, err=1, crit=1 ):
      return cls ( description, value, warn, err, crit )
   # --- end of new_fail_counter (...) ---

   def get_value ( self, unknown_value=0 ):
      v = self.value
      return v if v is not None else unknown_value
   # --- end of get_value (...) ---

   def get_value_str ( self, unknown_value="unknown" ):
      v = self.value
      return str ( v ) if v is not None else unknown_value
   # --- end of get_value_str (...) ---

   @property
   def value_str ( self ):
      return self.get_value_str()
   # --- end of value_str (...) ---

   def get_rating ( self, value ):
      if value is None:
         return self.STATUS_UNDEF

      else:
         too_high = lambda high, k: ( high is not None and k > high )
         too_low  = lambda low,  k: ( low  is not None and k < low  )
         ret = self.STATUS_NONE

         if too_high ( self.warn_high, value ):
            ret |= self.STATUS_WARN_HIGH

         if too_low ( self.warn_low, value ):
            ret |= self.STATUS_WARN_LOW

         if too_high ( self.err_high, value ):
            ret |= self.STATUS_ERR_HIGH

         if too_low ( self.err_low, value ):
            ret |= self.STATUS_ERR_LOW

         if too_high ( self.crit_high, value ):
            ret |= self.STATUS_CRIT_HIGH

         if too_low ( self.crit_low, value ):
            ret |= self.STATUS_CRIT_LOW

         return self.STATUS_OK if ret == self.STATUS_NONE else ret
   # --- end of get_rating (...) ---

   def is_warning ( self ):
      return self.status & self.STATUS_WARN
   # --- end of is_warning (...) ---

   def is_error ( self ):
      return self.status & self.STATUS_ERR
   # --- end of is_error (...) ---

   def is_critical ( self ):
      return self.status & self.STATUS_CRIT
   # --- end of is_critical (...) ---

   def has_issues ( self ):
      return self.status & self.STATUS_ISSUES
   # --- end of has_issues (...) ---

   def is_ok ( self ):
      return self.status == self.STATUS_OK
   # --- end of is_ok (...) ---

   def format_value ( self,
      fmt_ok=None, fmt_warn=None, fmt_err=None, fmt_crit=None, fmt_undef=None
   ):
      fmt = self.get_item ( fmt_ok, fmt_warn, fmt_err, fmt_crit, fmt_undef )
      if fmt:
         return fmt.format ( str ( self.value ) )
      elif fmt == "":
         return fmt
      else:
         return str ( self.value )
   # --- end of format_value (...) ---

   def get_item ( self, item_ok, item_warn, item_err, item_crit, item_undef ):
      status = self.status
      if self.status & self.STATUS_UNDEF:
         return item_undef
      elif self.status & self.STATUS_CRIT:
         return item_crit
      elif self.status & self.STATUS_ERR:
         return item_err
      elif self.status & self.STATUS_WARN:
         return item_warn
      else:
         return item_ok
   # --- end of get_item (...) ---

   def get_word ( self,
      word_ok="ok", word_warn="warn", word_err="err", word_crit="crit",
      word_undef="undef",
   ):
      return str ( self.get_item (
         word_ok, word_warn, word_err, word_crit, word_undef
      ) )
   # --- end of get_word (...) ---


# --- end of NumStatsCounterRating ---


class NumStatsRating ( StatsRating ):

   def __init__ ( self, values, description=None ):
      assert isinstance ( values, dict )
      super ( NumStatsRating, self ).__init__ ( description=description )
      self.values = values
      self.setup()
   # --- end of __init__ (...) ---

   @roverlay.util.objects.abstractmethod
   def setup ( self ):
      pass
   # --- end of setup (...) ---

   def get_rating ( self ):
      return self
   # --- end of get_rating (...) ---

# --- end of NumStatsRating ---


class RoverlayNumStatsRating ( NumStatsRating ):

   ## COULDFIX: yield str key / int indizes in get_suggestions() and
   ##           optionall "translate" them using a map
   ## "event" => message
   ##SUGGESTIONS = {}


   def setup ( self ):
      if __debug__:
         assert set ( NUMSTATS.keys() ) == set ( self.values.keys() )

      # FIXME: err/crit

      values = self.values

      # very efficient.
      # TODO/COULDFIX: find a better solution for handling UNKNOWNS
      # * 0 or 0 == 0 == None or 0
      # * don't use v_* as value when creating NumStatsCounterRating objects,
      #   the "UNKNOWN" state would get lost
      #
      v_pc_repo         = values['pc_repo']         or 0
      v_pc_distmap      = values['pc_distmap']      or 0
      v_pc_filtered     = values['pc_filtered']     or 0
      v_pc_queued       = values['pc_queued']       or 0
      v_pc_success      = values['pc_success']      or 0
      v_pc_fail         = values['pc_fail']         or 0
      v_pc_fail_empty   = values['pc_fail_empty']   or 0
      v_pc_fail_dep     = values['pc_fail_dep']     or 0
      v_pc_fail_selfdep = values['pc_fail_selfdep'] or 0
      v_pc_fail_err     = values['pc_fail_err']     or 0
      v_ec_pre          = values['ec_pre']          or 0
      v_ec_post         = values['ec_post']         or 0
      v_ec_written      = values['ec_written']      or 0
      v_ec_revbump      = values['ec_revbump']      or 0


      # *_high=k -- warn/... if value > k
      # *_low=k  -- warn/... if value < k
      new_numstats = lambda key, **b: (
         NumStatsCounterRating ( NUMSTATS[key], values[key], **b )
      )

      self.pc_repo = new_numstats ( 'pc_repo',
         warn_low = 1,
         err_low  = ( 1 if v_pc_distmap > 0 else 0 ),
      )

      self.pc_distmap = new_numstats ( 'pc_distmap',
         # src files of imported ebuilds don't get written to the distmap
         #  (can be "fixed" with --distmap-verify or distmap_rebuild command)
         warn_low  = max ( 1, v_ec_post ),
         err_low   = ( 1 if v_ec_post > 0 else 0 ),
         warn_high = ( ( 1.01 * v_ec_post ) if v_ec_post > 0 else None ),
         err_high  = ( ( 1.1  * v_ec_post ) if v_ec_post > 0 else None ),
      )

      self.pc_filtered = new_numstats ( 'pc_filtered',
         crit_high = ( v_pc_repo - v_pc_queued ),
      )

      self.pc_queued = new_numstats ( 'pc_queued',
         # cannot queue more packages than available
         crit_high = ( v_pc_repo - v_pc_filtered ),
      )

      self.pc_success = new_numstats ( 'pc_success',
         crit_high = v_pc_queued,
         # warn about low pc_success/pc_queued ratio
         warn_low = ( ( 0.9 * v_pc_queued ) if v_pc_queued > 0 else None ),
      )

      self.pc_fail = new_numstats ( 'pc_fail',
         # pc_queued would produce "false" warnings in incremental mode
         warn_high = max ( 0, 0.15 * v_pc_repo ),
         err_high  = max ( 0, 0.3  * v_pc_repo ),
         crit_high = max ( 0, 0.5  * v_pc_repo ),
         crit_low  = sum ((
            v_pc_fail_empty, v_pc_fail_dep, v_pc_fail_selfdep, v_pc_fail_err
         )),
      )

      self.pc_fail_empty   = new_numstats ( 'pc_fail_empty',
         crit_high = v_pc_fail,
      )
      self.pc_fail_dep     = new_numstats ( 'pc_fail_dep',
         crit_high = v_pc_fail,
         warn_high = max ( 10, ( 0.01 * v_pc_repo ) ),
      )
      self.pc_fail_selfdep = new_numstats ( 'pc_fail_selfdep',
         crit_high = v_pc_fail,
      )
      self.pc_fail_err     = new_numstats ( 'pc_fail_err',
         warn_high = 1,
         err_high  = 1,
         crit_high = v_pc_fail,
      )

      self.ec_pre    = new_numstats ( 'ec_pre',
         warn_high = v_ec_post,
         err_high  = max ( 0, ( 1.05 * v_ec_post ) ),
      )

      self.ec_post   = new_numstats ( 'ec_post',
         warn_low = v_ec_pre,
         # tolerate 5% ebuild loss (1/1.05 ~= 0.95)
         err_low  = max ( 1, ( 0.95 * v_ec_pre ) ),
      )
      self.ec_written = new_numstats ( 'ec_written',
         err_low = v_pc_success,
      )
      self.ec_revbump = new_numstats ( 'ec_revbump',
         crit_high = min ( v_pc_repo, v_ec_pre ),
         warn_high = min ( 1, ( 0.1 * v_ec_pre ) ),
      )
   # --- end of setup (...) ---

   def __iter__ ( self ):
      for key in NUMSTATS.keys():
         yield ( key, getattr ( self, key ) )
   # --- end of __iter__ (...) ---

   def get_suggestions ( self, pure_text=False ):
      if pure_text:
         code_format = { 'cstart': "\'", 'cend': "\'", }
      else:
         code_format = { 'cstart': "<code>", 'cend': "</code>", }


      if any ( value is None for value in self.values.values() ):
         yield (
            "database contains UNKNOWNS",
            [ "run roverlay", ]
         )

      if self.pc_repo.has_issues():
         yield (
            "low repo package count",
            [ "check the repo config file", "drop repos without packages" ]
         )

      if self.pc_distmap.has_issues():
         details = [
            'run {cstart}roverlay distmap_rebuild{cend}to fix '
            'the distmap'.format ( **code_format )
         ]

         if self.pc_distmap.status & self.STATUS_TOO_HIGH:
            topic = "distmap file count is higher than the ebuild count"
         else:
            topic = "distmap file count is lower than the ebuild count"
            details.append (
               'run {cstart}roverlay --fixup-category-move[-reverse]{cend} '
               ' after configuring relocations (in the package rules)'.format (
                  **code_format
               )
            )
         yield ( topic, details )


      if self.pc_success.get_value(2) < 1:
         if self.pc_success.status & (self.STATUS_ERR|self.STATUS_CRIT):
            yield ( "no ebuilds created", None )
         else:
            yield (
               "no ebuilds created (not an issue in incremental mode)",
               None
            )


      if self.pc_fail.get_value() > 0 or self.pc_success.has_issues():
         details = []
         if self.pc_fail_dep.get_value() > 0:
            details.append ( "write dependency rules" )
         details.append ( 'configure package ignore rules' )

         yield (
            '{adj} failure rate'.format (
               adj=self.pc_fail.get_word (
                  "normal/expected", "moderate", "high", "very high"
               )
            ),
            details
         )


      if self.pc_fail_err.has_issues():
         yield (
            "failures due to unknown errors",
            [ 'check the log files for python exceptions and report them', ]
         )

      if self.ec_pre.has_issues() or self.ec_post.has_issues():
         yield ( "ebuild loss occurred (no suggestions available)", None )

      if self.ec_revbump.has_issues():
         yield (
            "unexpected ebuild revbump count (no suggestions available)",
            None
         )

   # --- end of get_suggestions (...) ---

# --- end of RoverlayNumStatsRating ---
