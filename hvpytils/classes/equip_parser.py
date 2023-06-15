from urlpath import URL


class EquipParser:
    @classmethod
    def parse_equip_url(cls, url: str|URL) -> tuple[int, str]:
        """Extract (eid, key) from equip url"""
        
        # inits
        if isinstance(url, str): 
            url = URL(url)

        # parse based on url format
        if url.parts[1] == 'pages':
            # https://hentaiverse.org/pages/showequip.php?eid=83321433&key=96319d34f0
            eid = url.form['eid']
            key = url.form['key']
        elif url.parts[1] == 'equip':
            # https://hentaiverse.org/equip/277830473/2c877af3e9
            eid = url.parts[2]
            key = url.parts[3]
        else:
            raise ValueError
        
        # post procsesing
        eid = int(eid)
        key = str(key)

        # return
        return eid, key