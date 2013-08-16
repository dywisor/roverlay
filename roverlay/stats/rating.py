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


   STATUS_WARN_LOW  = STATUS_WARN | STATUS_TOO_LOW
   STATUS_WARN_HIGH = STATUS_WARN | STATUS_TOO_HIGH
   STATUS_ERR_LOW   = STATUS_ERR  | STATUS_TOO_LOW
   STATUS_ERR_HIGH  = STATUS_ERR  | STATUS_TOO_HIGH
   STATUS_CRIT_LOW  = STATUS_CRIT | STATUS_TOO_LOW
   STATUS_CRIT_HIGH = STATUS_CRIT | STATUS_TOO_HIGH

   STATUS_FAIL = ( ( 2**7 ) - 1 ) ^ STATUS_OK


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
      self.status    = (
         self.get_rating ( value ) if value is not None else None
      )
   # --- end of __init__ (...) ---

   @classmethod
   def new_fail_counter ( cls, description, value, warn=1, err=1, crit=1 ):
      return cls ( description, value, warn, err, crit )
   # --- end of new_fail_counter (...) ---

   def get_rating ( self, value ):
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

   def is_ok ( self ):
      return self.status == self.STATUS_OK
   # --- end of is_ok (...) ---

   def format_value ( self,
      fmt_ok=None, fmt_warn=None, fmt_err=None, fmt_crit=None
   ):
      fmt = self.get_item ( fmt_ok, fmt_warn, fmt_err, fmt_crit )
      if fmt:
         return fmt.format ( str ( self.value ) )
      elif fmt == "":
         return fmt
      else:
         return str ( self.value )
   # --- end of format_value (...) ---

   def get_item ( self, item_ok, item_warn, item_err, item_crit ):
      status = self.status
      if self.status & self.STATUS_CRIT:
         return item_crit
      elif self.status & self.STATUS_ERR:
         return item_err
      elif self.status & self.STATUS_WARN:
         return item_warn
      else:
         return item_ok
   # --- end of get_item (...) ---

   def get_word ( self,
      word_ok="ok", word_warn="warn", word_err="err", word_crit="crit"
   ):
      return str ( self.get_item ( word_ok, word_warn, word_err, word_crit ) )
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
      v_ec_post = values['ec_post']
      v_pc_repo = values['pc_repo']

      # *_high=k -- warn/... if value > k
      # *_low=k  -- warn/... if value < k
      new_numstats = lambda key, **b: (
         NumStatsCounterRating ( NUMSTATS[key], values[key], **b )
      )

      self.pc_repo = new_numstats ( 'pc_repo',
         warn_low=1,
         err_low=( 1 if values['pc_distmap'] > 0 else 0 ),
      )

      self.pc_distmap = new_numstats ( 'pc_distmap',
         # src files of imported ebuilds don't get written to the distmap
         #  (can be "fixed" with --distmap-verify)
         warn_low=max ( 1, v_ec_post ),
         err_low=( 1 if v_ec_post > 0 else 0 ),
         warn_high=( 1.01*v_ec_post if v_ec_post > 0 else None ),
         err_high=( 1.1*v_ec_post if v_ec_post > 0 else None ),
      )

      self.pc_filtered = new_numstats ( 'pc_filtered',
         crit_high=( v_pc_repo - values['pc_queued'] ),
      )

      self.pc_queued = new_numstats ( 'pc_queued',
         # cannot queue more packages than available
         crit_high=( v_pc_repo - values['pc_filtered'] ),
      )

      self.pc_success = new_numstats ( 'pc_success',
         crit_high=values['pc_queued'],
         # warn about low pc_success/pc_queued ratio
         warn_low=(
            0.9*values['pc_queued'] if values['pc_queued'] > 0 else None
         ),
      )

      self.pc_fail = new_numstats ( 'pc_fail',
         # pc_queued would produce "false" warnings in incremental mode
         warn_high=( max ( 0, 0.15 * v_pc_repo ) ),
         err_high=(  max ( 0, 0.3  * v_pc_repo ) ),
         crit_high=( max ( 0, 0.5  * v_pc_repo ) ),
         crit_low=(
            values['pc_fail_empty'] + values['pc_fail_dep']
            + values['pc_fail_selfdep'] + values['pc_fail_err']
         ),
      )

      self.pc_fail_empty   = new_numstats ( 'pc_fail_empty',
         crit_high=values['pc_fail'],
      )
      self.pc_fail_dep     = new_numstats ( 'pc_fail_dep',
         crit_high=values['pc_fail'],
         warn_high=max ( 10, 0.01*values['pc_repo'] ),
      )
      self.pc_fail_selfdep = new_numstats ( 'pc_fail_selfdep',
         crit_high=values['pc_fail'],
      )
      self.pc_fail_err     = new_numstats ( 'pc_fail_err',
         warn_high=1, err_high=1, crit_high=values['pc_fail'],
      )

      self.ec_pre     = new_numstats ( 'ec_pre',
         warn_high=v_ec_post,
         err_high=max ( 0, 1.05*v_ec_post ),
      )

      self.ec_post    = new_numstats ( 'ec_post',
         warn_low=values['ec_pre'],
         # tolerate 5% ebuild loss (1/1.05 ~= 0.95)
         err_low=max ( 1, 0.95*values['ec_pre'] ),
      )
      self.ec_written      = new_numstats ( 'ec_written',
         err_low=values['pc_success'],
      )
      self.ec_revbump = new_numstats ( 'ec_revbump',
         crit_high=min ( v_pc_repo, values['ec_pre'] ),
         warn_high=min ( 1, 0.1*values['ec_pre'] ),
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

      if not self.pc_repo.is_ok():
         yield (
            "low repo package count",
            [ "check the repo config file", "drop repos without packages" ]
         )

      if not self.pc_distmap.is_ok():
         details = [
            'run {cstart}roverlay --distmap-verify{cend} to fix '
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


      if self.pc_success.value < 1:
         if self.pc_success.status & (self.STATUS_ERR|self.STATUS_CRIT):
            yield ( "no ebuilds created", None )
         else:
            yield (
               "no ebuilds created (not an issue in incremental mode)",
               None
            )
      elif not self.pc_success.is_ok():
         yield (
            "only a few ebuilds created (not an issue in incremental mode)",
            None
         )

      if self.pc_fail.value > 0 or not self.pc_success.is_ok():
         details = []
         if self.pc_fail_dep.value > 0:
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



      if not self.pc_fail_err.is_ok():
         yield (
            "failures due to unknown errors",
            [ 'check the log files for python exceptions and report them', ]
         )

      if not self.ec_pre.is_ok() or not self.ec_post.is_ok():
         yield ( "ebuild loss occurred (no suggestions available)", None )

      if not self.ec_revbump.is_ok():
         yield (
            "unexpected ebuild revbump count (no suggestions available)",
            None
         )

   # --- end of get_suggestions (...) ---

# --- end of RoverlayNumStatsRating ---
