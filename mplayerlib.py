"""MPlayer slave mode interface by Fabien Devaux 

Found at http://code.activestate.com/recipes/542195/

Modifications by Rob McMullen
"""
import os, os.path, select, time, subprocess


class MPlayer(object):
    """ A class to access a slave mplayer process
    you may want to use command(name, args*) directly
    or call populate() to access functions (and minimal doc).

    Exemples:
        mp.command('loadfile', '/desktop/funny.mp3')
        mp.command('pause')
        mp.command('quit')

    Note:
        After a .populate() call, you can access an higher level interface:
            mp.loadfile('/desktop/funny.mp3')
            mp.pause()
            mp.quit()

        Beyond syntax, advantages are:
            - completion
            - minimal documentation
            - minimal return type parsing
    """

    exe_name = 'mplayer' if os.sep == '/' else 'mplayer.exe'

    def __init__(self, filename, *opts):
        self.filename = filename
        args = [self.exe_name]
        if opts:
            args.extend(opts)
        if "-slave" not in args:
            args.append("-slave")
#            args.append("-idle")
            args.append("-quiet") # Need this to force ANS output
        args.append(filename)
        print args
        self._mplayer = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=1)
        self._readlines()

    def _is_running(self):
        return (self._mplayer.poll() is None)
    
    def _get_property(self, prop_name):
        responses = self.command("pausing_keep_force get_property", prop_name)
        looking_for = "ANS_%s" % prop_name
        prop_val = None
        for line in responses:
            line = line.strip()
            print(line)
            if line.startswith(looking_for):
                dum, prop_val = line.split("=")
                print(prop_val)
        return prop_val
    
    def _get_int_property(self, prop_name):
        prop_val = self._get_property(prop_name)
        return int(prop_val)
    
    def _get_float_property(self, prop_name):
        prop_val = self._get_property(prop_name)
        return float(prop_val)
    
    def _get_current_pos(self):
        """Return the current position either in time or byte position
        depending on the type of media.  Byte position is only used for
        .vob rips
        
        Re-raises any exceptions if mplayer has already exited by the time this
        command is executed
        """
        last_pos = -1
        if self.filename.endswith(".vob"):
            try:
                last_pos = self._get_int_property("stream_pos")
            except:
                print("Failed checking stream_pos")
                raise
        else:
            try:
                last_pos = self._get_float_property("time_pos")
            except:
                print("Failed checking time_pos")
                raise
        return last_pos

    def _readlines(self):
        ret = []
        while any(select.select([self._mplayer.stdout.fileno()], [], [], 0.6)):
            ret.append( self._mplayer.stdout.readline() )
            if not self._is_running():
                break
        return ret

    def command(self, name, *args):
        """ Very basic interface [see populate()]
        Sends command 'name' to process, with given args
        """
        cmd = '%s%s%s\n'%(name,
                ' ' if args else '',
                ' '.join(repr(a) for a in args)
                )
        try:
            self._mplayer.stdin.write(cmd)
        except IOError:
            pass
        if name == 'quit':
            return
        return self._readlines()

    @classmethod
    def populate(kls):
        """ Populates this class by introspecting mplayer executable """
        mplayer = subprocess.Popen([kls.exe_name, '-input', 'cmdlist'],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE)

        def args_pprint(txt):
            lc = txt.lower()
            if lc[0] == '[':
                return '%s=None'%lc[1:-1]
            return lc

        while True:
            line = mplayer.stdout.readline()
            if not line:
                break
            if line[0].isupper():
                continue
            args = line.split()
            cmd_name = args.pop(0)
            arguments = ', '.join([args_pprint(a) for a in args])
            func_str = '''def _populated_fn(self, *args):
            """%(doc)s"""
            if not (%(minargc)d <= len(args) <= %(argc)d):
                raise TypeError('%(name)s takes %(argc)d arguments (%%d given)'%%len(args))
            ret = self.command('%(name)s', *args)
            if not ret:
                return None
            if ret[0].startswith('ANS'):
                val = ret[0].split('=', 1)[1].rstrip()
                try:
                    return eval(val)
                except:
                    return val
            return ret'''%dict(
                    doc = '%s(%s)'%(cmd_name, arguments),
                    minargc = len([a for a in args if a[0] != '[']),
                    argc = len(args),
                    name = cmd_name,
                    )
            exec(func_str)

            setattr(MPlayer, cmd_name, _populated_fn)

if __name__ == '__main__':
    import sys
    MPlayer.populate()
    try:
        mp = MPlayer(sys.argv[1])
        print mp._get_stats()
        last_stream_pos = 0
        while mp._is_running():
            responses = mp.command("get_property", "stream_pos")
            for line in responses:
                line = line.strip()
                print(line)
                if line.startswith("ANS_stream_pos"):
                    dum, last_stream_pos = line.split("=")
                    last_stream_pos = int(last_stream_pos)
                    print(last_stream_pos)
            time.sleep(1)
    except:
        raise
    finally:
        mp.quit()
